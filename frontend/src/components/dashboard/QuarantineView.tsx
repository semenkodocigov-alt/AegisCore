import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { QuarantinedFile } from '../../types/scanner';
import { apiService } from '../../services/api';

export const QuarantineView: React.FC = () => {
  const [items, setItems] = useState<QuarantinedFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');

  const loadItems = useCallback(async () => {
    setIsLoading(true);
    const response = await apiService.getQuarantineFiles();
    if (response.success && response.data) {
      setItems(response.data);
      setActionError('');
    } else {
      setActionError(response.error?.message || 'Quarantine contents could not be loaded.');
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void loadItems();
  }, [loadItems]);

  const runAction = async (item: QuarantinedFile, action: 'restore' | 'delete') => {
    setActionError('');
    setActionMessage('');
    const response = action === 'restore'
      ? await apiService.restoreQuarantineFile(item.id)
      : await apiService.deleteQuarantineFile(item.id);
    if (!response.success) {
      setActionError(response.error?.message || 'That action could not be completed.');
      return;
    }
    setItems((current) => current.filter((entry) => entry.id !== item.id));
    setActionMessage(action === 'restore'
      ? `Restored ${item.originalName}.`
      : `Removed ${item.originalName} from quarantine.`);
  };

  const purgeAll = async () => {
    if (!items.length || !window.confirm(`Permanently remove all ${items.length} quarantined files?`)) return;
    setActionError('');
    setActionMessage('');
    const outcomes = await Promise.all(items.map((item) => apiService.deleteQuarantineFile(item.id)));
    const deletedIds = new Set(
      outcomes.flatMap((result, index) => result.success ? [items[index].id] : []),
    );
    setItems((current) => current.filter((item) => !deletedIds.has(item.id)));
    const failedCount = outcomes.length - deletedIds.size;
    if (failedCount) {
      setActionError(`${failedCount} file${failedCount === 1 ? '' : 's'} could not be removed. Refresh and try again.`);
    } else {
      setActionMessage(`Removed ${items.length} files from quarantine.`);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <motion.section
      className="quarantine-page"
      initial={{ opacity: 0, y: 7 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 340, damping: 32 }}
    >
      <header className="page-heading">
        <div>
          <p className="eyebrow">LOCAL STORAGE</p>
          <h1>Quarantine</h1>
          <p>Review isolated files before restoring or removing them.</p>
        </div>
        <button className="button button-secondary" type="button" onClick={() => void purgeAll()} disabled={!items.length || isLoading}>
          Remove all
        </button>
      </header>

      <AnimatePresence>
        {(actionError || actionMessage) && (
          <motion.div
            className={`account-notice ${actionError ? 'account-notice-error' : ''}`}
            role={actionError ? 'alert' : 'status'}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            {actionError || actionMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {isLoading ? (
        <div className="account-card quarantine-empty">Loading quarantine…</div>
      ) : items.length === 0 ? (
        <div className="account-card quarantine-empty">
          <p className="eyebrow">NOTHING IS ISOLATED</p>
          <h2>Quarantine is empty</h2>
          <p>Files you move here will appear in this list.</p>
        </div>
      ) : (
        <div className="account-card quarantine-table-wrap">
          <table className="quarantine-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Original location</th>
                <th>Size</th>
                <th>Moved to quarantine</th>
                <th><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.originalName}</strong>
                    <small>{item.threatName}</small>
                  </td>
                  <td className="quarantine-path" title={item.originalPath}>{item.originalPath}</td>
                  <td>{formatSize(item.size)}</td>
                  <td>{item.quarantinedAt}</td>
                  <td className="quarantine-actions">
                    <button className="button button-secondary" type="button" onClick={() => void runAction(item, 'restore')}>
                      Restore
                    </button>
                    <button className="button button-danger" type="button" onClick={() => void runAction(item, 'delete')}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.section>
  );
};
