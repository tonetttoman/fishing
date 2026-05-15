import { useEffect, useMemo, useRef, useState } from 'react';

const MIN_SECONDS = 5;
const MAX_SECONDS = 60 * 60;
const DEFAULT_SECONDS = 5 * 60;

function clampSeconds(value: number) {
  return Math.min(MAX_SECONDS, Math.max(MIN_SECONDS, Math.round(value)));
}

function formatClock(totalSeconds: number) {
  const absolute = Math.abs(totalSeconds);
  const minutes = Math.floor(absolute / 60);
  const seconds = absolute % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function App() {
  const [configuredSeconds, setConfiguredSeconds] = useState(DEFAULT_SECONDS);
  const [displaySeconds, setDisplaySeconds] = useState(DEFAULT_SECONDS);
  const [isRunning, setIsRunning] = useState(false);
  const [hasExpired, setHasExpired] = useState(false);
  const [isSettingLocked, setIsSettingLocked] = useState(true);

  const deadlineRef = useRef<number | null>(null);
  const tickTimerRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const alarmPlayedRef = useRef(false);

  const displayLabel = useMemo(() => formatClock(displaySeconds), [displaySeconds]);

  useEffect(() => {
    return () => {
      if (tickTimerRef.current !== null) {
        window.clearInterval(tickTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isRunning) {
      if (tickTimerRef.current !== null) {
        window.clearInterval(tickTimerRef.current);
        tickTimerRef.current = null;
      }

      return;
    }

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
    if (!hasExpired || alarmPlayedRef.current) {
      return;
    }

    alarmPlayedRef.current = true;
    playBeep();
  }, [hasExpired]);

  const ensureAudioContext = async () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new window.AudioContext();
    }

    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume();
    }

    return audioContextRef.current;
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
    alarmPlayedRef.current = false;
    deadlineRef.current = Date.now() + configuredSeconds * 1000;
    setDisplaySeconds(configuredSeconds);
    setHasExpired(false);
    setIsRunning(true);
  };

  const updateConfiguredTime = (nextValue: number) => {
    const safeValue = clampSeconds(nextValue);
    setConfiguredSeconds(safeValue);

    if (!isRunning) {
      setDisplaySeconds(safeValue);
    }
  };

  const primaryLabel = isRunning ? 'Újradobás' : 'Indítás';

  return (
    <main className="app-shell">
      <section className="timer-card">
        <div className={`timer-face ${hasExpired ? 'timer-face--expired' : ''}`}>
          <span className="timer-label">{hasExpired ? 'Túlcsúszás' : 'Hátralévő idő'}</span>
          <strong className="timer-value">{displayLabel}</strong>
        </div>

        <button
          className={`primary-action ${hasExpired ? 'primary-action--expired' : ''}`}
          type="button"
          onClick={restartTimer}
        >
          {primaryLabel}
        </button>

        <section className={`setting-panel ${isSettingLocked ? 'setting-panel--locked' : ''}`} aria-label="Idő beállítása">
          <div className="setting-header">
            <div>
              <p className="setting-label">Beállított idő</p>
              <strong className="setting-value">{formatClock(configuredSeconds)}</strong>
            </div>
            <button
              className="lock-button"
              type="button"
              onClick={() => setIsSettingLocked((current) => !current)}
              aria-pressed={isSettingLocked}
            >
              {isSettingLocked ? 'Zárva' : 'Nyitva'}
            </button>
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
        </section>
      </section>
    </main>
  );
}

export default App;
