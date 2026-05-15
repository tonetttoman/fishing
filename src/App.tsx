import { useEffect, useMemo, useRef, useState } from 'react';

const MIN_SECONDS = 5;
const MAX_SECONDS = 60 * 60;
const DEFAULT_SECONDS = 2 * 60 + 30;
const SESSION_IDLE_RESET_SECONDS = 60 * 60;

type WakeLockSentinelLike = {
  release: () => Promise<void>;
  addEventListener: (type: 'release', listener: () => void) => void;
};

type NavigatorWithWakeLock = Navigator & {
  wakeLock?: {
    request: (type: 'screen') => Promise<WakeLockSentinelLike>;
  };
};

function clampSeconds(value: number) {
  return Math.min(MAX_SECONDS, Math.max(MIN_SECONDS, Math.round(value)));
}

function formatClock(totalSeconds: number) {
  const absolute = Math.abs(totalSeconds);
  const minutes = Math.floor(absolute / 60);
  const seconds = absolute % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function formatSessionClock(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function formatDate(date: Date) {
  return new Intl.DateTimeFormat('hu-HU', {
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

function formatTime(date: Date) {
  return new Intl.DateTimeFormat('hu-HU', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function App() {
  const [configuredSeconds, setConfiguredSeconds] = useState(DEFAULT_SECONDS);
  const [displaySeconds, setDisplaySeconds] = useState(DEFAULT_SECONDS);
  const [isRunning, setIsRunning] = useState(false);
  const [hasExpired, setHasExpired] = useState(false);
  const [isSettingLocked, setIsSettingLocked] = useState(true);
  const [fishCount, setFishCount] = useState(0);
  const [castCount, setCastCount] = useState(0);
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [isSessionRunning, setIsSessionRunning] = useState(false);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [lastSessionActivityAt, setLastSessionActivityAt] = useState<number | null>(null);

  const deadlineRef = useRef<number | null>(null);
  const tickTimerRef = useRef<number | null>(null);
  const clockTimerRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const alarmPlayedRef = useRef(false);
  const wakeLockRef = useRef<WakeLockSentinelLike | null>(null);

  const displayLabel = useMemo(() => formatClock(displaySeconds), [displaySeconds]);
  const dateLabel = useMemo(() => formatDate(currentDate), [currentDate]);
  const timeLabel = useMemo(() => formatTime(currentDate), [currentDate]);
  const sessionLabel = useMemo(() => formatSessionClock(sessionSeconds), [sessionSeconds]);

  useEffect(() => {
    clockTimerRef.current = window.setInterval(() => {
      setCurrentDate(new Date());
      setSessionSeconds((current) => (isSessionRunning ? current + 1 : current));

      if (lastSessionActivityAt !== null && Date.now() - lastSessionActivityAt >= SESSION_IDLE_RESET_SECONDS * 1000) {
        setIsSessionRunning(false);
        setSessionSeconds(0);
        setLastSessionActivityAt(null);
      }
    }, 1000);

    return () => {
      if (tickTimerRef.current !== null) {
        window.clearInterval(tickTimerRef.current);
      }

      if (clockTimerRef.current !== null) {
        window.clearInterval(clockTimerRef.current);
      }

      releaseWakeLock();
    };
  }, [isSessionRunning, lastSessionActivityAt]);

  useEffect(() => {
    if (!isRunning) {
      if (tickTimerRef.current !== null) {
        window.clearInterval(tickTimerRef.current);
        tickTimerRef.current = null;
      }

      releaseWakeLock();
      return;
    }

    requestWakeLock();

    const updateDisplay = () => {
      if (deadlineRef.current === null) {
        return;
      }

      const secondsLeft = Math.ceil((deadlineRef.current - Date.now()) / 1000);
      setDisplaySeconds(secondsLeft);

      if (secondsLeft <= 0 && !hasExpired) {
        setHasExpired(true);
      }
    };

    updateDisplay();
    tickTimerRef.current = window.setInterval(updateDisplay, 250);

    return () => {
      if (tickTimerRef.current !== null) {
        window.clearInterval(tickTimerRef.current);
        tickTimerRef.current = null;
      }
    };
  }, [hasExpired, isRunning]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isRunning) {
        requestWakeLock();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isRunning]);

  useEffect(() => {
    if (!hasExpired || alarmPlayedRef.current) {
      return;
    }

    alarmPlayedRef.current = true;
    playAlarm();
  }, [hasExpired]);

  const requestWakeLock = async () => {
    try {
      const wakeLock = (navigator as NavigatorWithWakeLock).wakeLock;

      if (!wakeLock || wakeLockRef.current) {
        return;
      }

      wakeLockRef.current = await wakeLock.request('screen');
      wakeLockRef.current.addEventListener('release', () => {
        wakeLockRef.current = null;
      });
    } catch {
      wakeLockRef.current = null;
    }
  };

  const releaseWakeLock = async () => {
    if (!wakeLockRef.current) {
      return;
    }

    try {
      await wakeLockRef.current.release();
    } catch {
      // Ha a rendszer már elengedte, nincs több dolgunk vele.
    } finally {
      wakeLockRef.current = null;
    }
  };

  const ensureAudioContext = async () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new window.AudioContext();
    }

    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume();
    }

    return audioContextRef.current;
  };

  const markSessionActivity = () => {
    setLastSessionActivityAt(Date.now());
  };

  const vibrateAlarm = () => {
    if ('vibrate' in navigator) {
      navigator.vibrate([260, 120, 260, 120, 520]);
    }
  };

  const playAlarm = () => {
    vibrateAlarm();
    playBeep();
  };

  const playBeep = async () => {
    try {
      const context = await ensureAudioContext();
      const oscillator = context.createOscillator();
      const gainNode = context.createGain();

      oscillator.type = 'square';
      oscillator.frequency.value = 880;
      gainNode.gain.setValueAtTime(0.0001, context.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.22, context.currentTime + 0.02);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.36);

      oscillator.connect(gainNode);
      gainNode.connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.38);
    } catch {
      // A böngésző hangblokkolása nem állíthatja meg a timer működését.
    }
  };

  const restartTimer = async () => {
    await ensureAudioContext();
    await requestWakeLock();
    alarmPlayedRef.current = false;
    deadlineRef.current = Date.now() + configuredSeconds * 1000;
    setDisplaySeconds(configuredSeconds);
    setHasExpired(false);
    setIsRunning(true);
    setCastCount((current) => current + 1);
    markSessionActivity();
  };

  const updateConfiguredTime = (nextValue: number) => {
    const safeValue = clampSeconds(nextValue);
    setConfiguredSeconds(safeValue);

    if (!isRunning) {
      setDisplaySeconds(safeValue);
    }
  };

  const incrementFishCount = () => {
    setFishCount((current) => current + 1);
    markSessionActivity();
  };

  const decrementFishCount = () => {
    setFishCount((current) => Math.max(0, current - 1));
  };

  const decrementCastCount = () => {
    setCastCount((current) => Math.max(0, current - 1));
  };

  const resetCastCount = () => {
    setCastCount(0);
  };

  const toggleSessionTimer = () => {
    setIsSessionRunning((current) => {
      const nextValue = !current;

      if (nextValue) {
        setLastSessionActivityAt(Date.now());
      }

      return nextValue;
    });
  };

  return (
    <main className="app-shell">
      <section className="timer-card">
        <section className={`timer-panel ${hasExpired ? 'timer-panel--expired' : ''}`}>
          <div className="date-display">{dateLabel}</div>
          <div className="time-display">{timeLabel}</div>
          <button
            className="timer-main-button"
            type="button"
            onClick={restartTimer}
            aria-label="Újradobás időzítő indítása"
          >
            <strong className="timer-value">{displayLabel}</strong>
          </button>
          {!isSettingLocked ? (
            <button className="cast-minus-button" type="button" onClick={decrementCastCount} aria-label="Dobás számláló csökkentése">
              −
            </button>
          ) : null}
          <span className="cast-count-badge">{castCount}</span>
        </section>

        <section className="fish-counter" aria-label="Hal számláló">
          <button className="fish-count-button" type="button" onClick={incrementFishCount}>
            <strong className="fish-count-value">{fishCount}</strong>
          </button>
          {!isSettingLocked ? (
            <button className="fish-minus-button" type="button" onClick={decrementFishCount} aria-label="Hal számláló csökkentése">
              −
            </button>
          ) : null}
        </section>

        <section className={`setting-panel ${isSettingLocked ? 'setting-panel--locked' : ''}`} aria-label="Idő beállítása">
          <div className="setting-header">
            <strong className="setting-value">{formatClock(configuredSeconds)}</strong>
            <div className="setting-actions">
              {!isSettingLocked ? (
                <button
                  className={`session-button ${isSessionRunning ? 'session-button--running' : ''}`}
                  type="button"
                  onClick={toggleSessionTimer}
                  aria-label="Session időzítő indítása vagy megállítása"
                >
                  {sessionLabel}
                </button>
              ) : null}
              <button
                className="lock-button"
                type="button"
                onClick={() => setIsSettingLocked((current) => !current)}
                aria-pressed={isSettingLocked}
              >
                {isSettingLocked ? '🔒' : '🔓'}
              </button>
            </div>
          </div>

          <input
            className="time-slider"
            type="range"
            min={MIN_SECONDS}
            max={MAX_SECONDS}
            step={5}
            value={configuredSeconds}
            disabled={isSettingLocked}
            onChange={(event) => updateConfiguredTime(Number(event.target.value))}
            aria-label="Visszaszámláló ideje"
          />

          {!isSettingLocked ? (
            <button className="cast-reset-button" type="button" onClick={resetCastCount}>
              0
            </button>
          ) : null}
        </section>
      </section>
    </main>
  );
}

export default App;
