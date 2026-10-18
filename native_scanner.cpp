#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <system_error>
#include <unordered_map>
#include <vector>

#pragma comment(lib, "bcrypt.lib")

namespace {

constexpr std::size_t kChunkSize = 1024 * 1024;
constexpr std::size_t kEntropySampleSize = 10000;
constexpr std::size_t kErrorBufferSize = 512;

std::wstring to_wide(const char* text) {
    if (text == nullptr || *text == '\0') {
        return {};
    }
    const int required = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text, -1, nullptr, 0);
    if (required <= 0) {
        return {};
    }
    std::wstring result(static_cast<std::size_t>(required), L'\0');
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text, -1, result.data(), required) <= 0) {
        return {};
    }
    result.pop_back();
    return result;
}

void set_error(char* output, std::size_t output_size, const char* message) {
    if (output == nullptr || output_size == 0) {
        return;
    }
    const std::size_t length = std::min(output_size - 1, std::strlen(message));
    std::memcpy(output, message, length);
    output[length] = '\0';
}

std::string to_utf8(const std::wstring& text) {
    if (text.empty()) {
        return {};
    }
    const int required = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(),
                                              static_cast<int>(text.size()), nullptr, 0, nullptr, nullptr);
    if (required <= 0) {
        return {};
    }
    std::string result(static_cast<std::size_t>(required), '\0');
    if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(),
                            static_cast<int>(text.size()), result.data(), required, nullptr, nullptr) <= 0) {
        return {};
    }
    return result;
}

class HashState {
public:
    explicit HashState(LPCWSTR algorithm) {
        if (BCryptOpenAlgorithmProvider(&algorithm_, algorithm, nullptr, 0) < 0) {
            return;
        }
        DWORD object_size = 0;
        DWORD result_size = 0;
        if (BCryptGetProperty(algorithm_, BCRYPT_OBJECT_LENGTH,
                              reinterpret_cast<PUCHAR>(&object_size), sizeof(object_size),
                              &result_size, 0) < 0) {
            return;
        }
        if (BCryptGetProperty(algorithm_, BCRYPT_HASH_LENGTH,
                              reinterpret_cast<PUCHAR>(&digest_size_), sizeof(digest_size_),
                              &result_size, 0) < 0) {
            return;
        }
        object_.resize(object_size);
        digest_.resize(digest_size_);
        if (BCryptCreateHash(algorithm_, &hash_, object_.data(), object_size, nullptr, 0, 0) >= 0) {
            ready_ = true;
        }
    }

    ~HashState() {
        if (hash_ != nullptr) {
            BCryptDestroyHash(hash_);
        }
        if (algorithm_ != nullptr) {
            BCryptCloseAlgorithmProvider(algorithm_, 0);
        }
    }

    HashState(const HashState&) = delete;
    HashState& operator=(const HashState&) = delete;

    bool ready() const { return ready_; }

    bool update(PUCHAR data, ULONG size) {
        return BCryptHashData(hash_, data, size, 0) >= 0;
    }

    bool finish() {
        return BCryptFinishHash(hash_, digest_.data(), digest_size_, 0) >= 0;
    }

    std::string hex_digest() const {
        static constexpr char digits[] = "0123456789abcdef";
        std::string result(digest_.size() * 2, '\0');
        for (std::size_t i = 0; i < digest_.size(); ++i) {
            result[i * 2] = digits[digest_[i] >> 4];
            result[i * 2 + 1] = digits[digest_[i] & 0x0f];
        }
        return result;
    }

private:
    BCRYPT_ALG_HANDLE algorithm_ = nullptr;
    BCRYPT_HASH_HANDLE hash_ = nullptr;
    std::vector<UCHAR> object_;
    std::vector<UCHAR> digest_;
    DWORD digest_size_ = 0;
    bool ready_ = false;
};

double entropy_from_counts(const std::array<std::uint64_t, 256>& counts, std::uint64_t size) {
    if (size == 0) {
        return 0.0;
    }
    double entropy = 0.0;
    for (const auto count : counts) {
        if (count == 0) {
            continue;
        }
        const double probability = static_cast<double>(count) / static_cast<double>(size);
        entropy -= probability * std::log2(probability);
    }
    return entropy;
}

using FileCallback = int(__cdecl*)(const char*, void*);

struct SignatureIndex {
    std::mutex mutex;
    std::unordered_map<std::string, std::string> signatures;
};

struct WalkContext {
    FileCallback callback;
    void* user_data;
    std::size_t max_files;
    std::size_t files_seen = 0;
};

bool is_reparse_point(const std::filesystem::path& path) {
    const DWORD attributes = GetFileAttributesW(path.c_str());
    return attributes != INVALID_FILE_ATTRIBUTES &&
           (attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0;
}

void walk_directory(const std::filesystem::path& directory, int depth, int max_depth,
                    WalkContext& context) {
    if (context.files_seen >= context.max_files) {
        return;
    }

    std::error_code error;
    std::filesystem::directory_iterator iterator(
        directory, std::filesystem::directory_options::skip_permission_denied, error);
    const std::filesystem::directory_iterator end;
    while (!error && iterator != end && context.files_seen < context.max_files) {
        const auto entry = *iterator;
        std::error_code entry_error;
        const auto entry_path = entry.path();
        const bool directory_entry = entry.is_directory(entry_error);
        if (!entry_error && !is_reparse_point(entry_path)) {
            if (directory_entry) {
                if (depth < max_depth) {
                    walk_directory(entry_path, depth + 1, max_depth, context);
                }
            } else if (entry.is_regular_file(entry_error) && !entry_error) {
                const std::string encoded_path = to_utf8(entry_path.native());
                if (!encoded_path.empty()) {
                    ++context.files_seen;
                    if (context.callback(encoded_path.c_str(), context.user_data) == 0) {
                        return;
                    }
                }
            }
        }
        iterator.increment(error);
        if (error) {
            error.clear();
        }
    }
}

}  // namespace

extern "C" __declspec(dllexport) int __cdecl aegis_hash_file(
    const char* path_utf8,
    char* md5_output,
    char* sha1_output,
    char* sha256_output,
    double* entropy_output,
    char* error_output,
    std::size_t error_output_size) {
    const std::wstring path = to_wide(path_utf8);
    if (path.empty()) {
        set_error(error_output, error_output_size, "Invalid UTF-8 file path.");
        return 1;
    }

    HashState md5(BCRYPT_MD5_ALGORITHM);
    HashState sha1(BCRYPT_SHA1_ALGORITHM);
    HashState sha256(BCRYPT_SHA256_ALGORITHM);
    if (!md5.ready() || !sha1.ready() || !sha256.ready()) {
        set_error(error_output, error_output_size, "Windows CNG could not initialize hash providers.");
        return 2;
    }

    HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              nullptr, OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
    if (file == INVALID_HANDLE_VALUE) {
        set_error(error_output, error_output_size, "Could not open file for native hashing.");
        return 3;
    }

    std::vector<UCHAR> buffer(kChunkSize);
    std::array<std::uint64_t, 256> entropy_counts{};
    std::uint64_t entropy_bytes = 0;
    bool succeeded = true;
    DWORD bytes_read = 0;
    do {
        if (!ReadFile(file, buffer.data(), static_cast<DWORD>(buffer.size()), &bytes_read, nullptr)) {
            succeeded = false;
            break;
        }
        if (bytes_read == 0) {
            break;
        }
        succeeded = md5.update(buffer.data(), bytes_read) &&
                    sha1.update(buffer.data(), bytes_read) &&
                    sha256.update(buffer.data(), bytes_read);
        if (!succeeded) {
            break;
        }
        const std::size_t sample_count = std::min<std::size_t>(
            bytes_read, kEntropySampleSize - static_cast<std::size_t>(entropy_bytes));
        for (std::size_t i = 0; i < sample_count; ++i) {
            ++entropy_counts[buffer[i]];
        }
        entropy_bytes += sample_count;
    } while (bytes_read == buffer.size());

    CloseHandle(file);
    if (!succeeded || !md5.finish() || !sha1.finish() || !sha256.finish()) {
        set_error(error_output, error_output_size, "Native file hashing failed.");
        return 4;
    }
    const auto copy_digest = [](const std::string& digest, char* output) {
        if (output != nullptr) {
            std::memcpy(output, digest.c_str(), digest.size() + 1);
        }
    };
    copy_digest(md5.hex_digest(), md5_output);
    copy_digest(sha1.hex_digest(), sha1_output);
    copy_digest(sha256.hex_digest(), sha256_output);
    if (entropy_output != nullptr) {
        *entropy_output = entropy_from_counts(entropy_counts, entropy_bytes);
    }
    return 0;
}

extern "C" __declspec(dllexport) double __cdecl aegis_entropy(
    const unsigned char* data, std::size_t size) {
    if (data == nullptr || size == 0) {
        return 0.0;
    }
    std::array<std::uint64_t, 256> counts{};
    for (std::size_t i = 0; i < size; ++i) {
        ++counts[data[i]];
    }
    return entropy_from_counts(counts, size);
}

extern "C" __declspec(dllexport) void* __cdecl aegis_signature_index_create() {
    return new (std::nothrow) SignatureIndex();
}

extern "C" __declspec(dllexport) void __cdecl aegis_signature_index_clear(void* handle) {
    if (handle == nullptr) {
        return;
    }
    auto& index = *static_cast<SignatureIndex*>(handle);
    std::lock_guard<std::mutex> lock(index.mutex);
    index.signatures.clear();
}

extern "C" __declspec(dllexport) int __cdecl aegis_signature_index_add(
    void* handle, const char* hash, const char* name) {
    if (handle == nullptr || hash == nullptr || name == nullptr) {
        return 0;
    }
    auto& index = *static_cast<SignatureIndex*>(handle);
    std::lock_guard<std::mutex> lock(index.mutex);
    index.signatures[hash] = name;
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl aegis_signature_index_match(
    void* handle, const char* md5, const char* sha1, const char* sha256,
    int sha256_first, char* name_output, std::size_t name_output_size) {
    if (handle == nullptr || name_output == nullptr || name_output_size == 0) {
        return -1;
    }
    auto& index = *static_cast<SignatureIndex*>(handle);
    std::lock_guard<std::mutex> lock(index.mutex);
    const std::array<const char*, 3> ordered_hashes = sha256_first
        ? std::array<const char*, 3>{sha256, sha1, md5}
        : std::array<const char*, 3>{md5, sha1, sha256};
    for (const char* hash : ordered_hashes) {
        if (hash == nullptr || *hash == '\0') {
            continue;
        }
        const auto found = index.signatures.find(hash);
        if (found != index.signatures.end()) {
            const std::size_t length = std::min(name_output_size - 1, found->second.size());
            std::memcpy(name_output, found->second.data(), length);
            name_output[length] = '\0';
            return 1;
        }
    }
    return 0;
}

extern "C" __declspec(dllexport) void __cdecl aegis_signature_index_destroy(void* handle) {
    delete static_cast<SignatureIndex*>(handle);
}

extern "C" __declspec(dllexport) long long __cdecl aegis_walk_directory(
    const char* root_utf8, int max_depth, std::size_t max_files,
    FileCallback callback, void* user_data) {
    const std::wstring root = to_wide(root_utf8);
    if (root.empty() || callback == nullptr || max_depth < 0) {
        return -1;
    }
    std::error_code error;
    const std::filesystem::path root_path(root);
    if (!std::filesystem::is_directory(root_path, error) || error) {
        return -1;
    }
    WalkContext context{callback, user_data, max_files};
    walk_directory(root_path, 0, max_depth, context);
    return static_cast<long long>(context.files_seen);
}
