import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TitleBar } from './components/common/TitleBar';
import { SplashScreen } from './components/common/SplashScreen';
import { Navigation, ActiveTab } from './components/dashboard/Navigation';
import { StatusHeader } from './components/dashboard/StatusHeader';
import { ScanConsole } from './components/dashboard/ScanConsole';
import { QuarantineView } from './components/dashboard/QuarantineView';
import { SettingsView } from './components/dashboard/SettingsView';
import { AccountView } from './components/dashboard/AccountView';
import { WelcomeScreen } from './components/auth/WelcomeScreen';
import { apiService } from './services/api';

const AppContent: React.FC = () => {
  const [isInitializing, setIsInitializing] = useState(true);
  const [hasRestoredSession, setHasRestoredSession] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>('scanner');
  const [quarantinedCount, setQuarantinedCount] = useState(0);
  const { isLoading, isAuthenticated, continueAsGuest } = useAuth();
  const finishInitialization = useCallback(() => setIsInitializing(false), []);

  useEffect(() => {
    if (!isLoading) setHasRestoredSession(true);
  }, [isLoading]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let isActive = true;
    void apiService.getQuarantineFiles().then((response) => {
      if (isActive && response.success && response.data) {
        setQuarantinedCount(response.data.length);
      }
    });
    return () => {
      isActive = false;
    };
  }, [isAuthenticated]);

  const handleThreatQuarantined = () => setQuarantinedCount((count) => count + 1);

  return (
    <div className="app-frame">
      <TitleBar />

      <AnimatePresence>
        {(isInitializing || !hasRestoredSession) && (
          <SplashScreen onComplete={finishInitialization} minDurationMs={1250} />
        )}
      </AnimatePresence>

      {hasRestoredSession && !isInitializing && (
        <AnimatePresence mode="wait" initial={false}>
          {isAuthenticated ? (
            <motion.div
              className="app-shell"
              key="workspace"
              initial={{ opacity: 0, y: 7 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            >
              <Navigation
                activeTab={activeTab}
                onTabChange={setActiveTab}
                quarantineCount={quarantinedCount}
              />
              <main className="app-main dashboard-content">
                {activeTab === 'scanner' && <StatusHeader quarantinedCount={quarantinedCount} />}
                <AnimatePresence mode="wait" initial={false}>
                  <motion.section
                    className="tab-page"
                    key={activeTab}
                    initial={{ opacity: 0, y: 7 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    transition={{ type: 'spring', stiffness: 340, damping: 34 }}
                  >
                    {activeTab === 'scanner' && (
                      <ScanConsole onThreatQuarantined={handleThreatQuarantined} />
                    )}
                    {activeTab === 'quarantine' && <QuarantineView />}
                    {activeTab === 'settings' && <SettingsView />}
                    {activeTab === 'account' && <AccountView />}
                  </motion.section>
                </AnimatePresence>
              </main>
            </motion.div>
          ) : (
            <motion.div
              className="app-shell"
              key="welcome"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <WelcomeScreen onContinueAsGuest={() => continueAsGuest()} />
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </div>
  );
};

export const App: React.FC = () => (
  <ThemeProvider>
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  </ThemeProvider>
);

export default App;
