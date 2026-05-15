import { useEffect, useMemo, useRef, useState } from 'react';

const MIN_SECONDS = 30;
const MAX_SECONDS = 30 * 60;
const DEFAULT_SECONDS = 5 * 60;

function clampSeconds(value: number) {
  return Math.min(MAX_SECONDS, Math.max(MIN_SECONDS, Math.round(value)));
}

function formatClock(totalSeconds: number) {
  const absolute = Math.abs(totalSeconds);
  const minutes = Math.floor(absolute / 60);
  const seconds = absolute % 60;
  const prefix = totalSeconds < 0 ? '+' : '';
  return `${prefix}${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function App() {
  const [configuredSeconds, setConfiguredSeconds] = useState(DEFAULT_SECONDS);
  const [displaySeconds, setDisplaySeconds] = useState(DEFAULT_SECONDS);
  const [isRunning, setIsRunning] = useState(false);
  const [hasExpired, setHasExpired] = useState(false);
  const [audioUnlocked, setAudioUnlocked] = useState(false);

  const deadlineRef = useRef<number | null>(null);
  const tickTimerRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const alarmIntervalRef = useRef<number | null>(null);

  const displayLabel = useMemo(() => formatClock(displaySeconds), [displaySeconds]);

  useEffect(() => {
    return () => {
      if (tickTimerRef.current !== null) {
        window.clearInterval(tickTimerRef.current);
      }

      if (alarmIntervalRef.current !== null) {
        window.clearInterval(alarmIntervalRef.current);
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
    if (!hasExpired) {
      if (alarmIntervalRef.current !== null) {
        window.clearInterval(alarmIntervalRef.current);
        alarmIntervalRef.current = null;
      }

      return;
    }

    playBeep();
    alarmIntervalRef.current = window.setInterval(() => {
      playBeep();
    }, 1800);

    return () => {
      if (alarmIntervalRef.current !== null) {
        window.clearInterval(alarmIntervalRef.current);
        alarmIntervalRef.current = null;
      }
    };
  }, [hasExpired]);

  const ensureAudioContext = async () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new window.AudioContext();
    }

    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume();
    }

    setAudioUnlocked(true);
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
      setAudioUnlocked(false);
    }
  };

  const startTimer = async () => {
    await ensureAudioContext();
    deadlineRef.current = Date.now() + displaySeconds * 1000;
    setHasExpired(false);
    setIsRunning(true);
  };

  const handlePrimaryAction = async () => {
    if (hasExpired) {
      await ensureAudioContext();
      deadlineRef.current = Date.now() + configuredSeconds * 1000;
      setDisplaySeconds(configuredSeconds);
      setHasExpired(false);
      setIsRunning(true);
      return;
    }

    if (isRunning) {
      setIsRunning(false);
      return;
    }

    await startTimer();
  };

  const handleReset = () => {
    setIsRunning(false);
    setHasExpired(false);
    setDisplaySeconds(configuredSeconds);
    deadlineRef.current = null;
  };

  const updateConfiguredTime = (nextValue: number) => {
    const safeValue = clampSeconds(nextValue);
    setConfiguredSeconds(safeValue);

    if (!isRunning) {
      setDisplaySeconds(safeValue);
    }
  };

  const primaryLabel = hasExpired ? 'Újradobás' : isRunning ? 'Szünet' : 'Indítás';

  return (
    <main className="app-shell">
      <section className="timer-card">
        <div className={`timer-face ${hasExpired ? 'timer-face--expired' : ''}`}>
          <span className="timer-label">{hasExpired ? 'Túlcsúszás' : 'Hátralévő idő'}</span>
          <strong className="timer-value">{displayLabel}</strong>
        </div>

        <div className="controls">
          <button className="primary-action" type="button" onClick={handlePrimaryAction}>
            {primaryLabel}
          </button>
          <button className="secondary-action" type="button" onClick={handleReset}>
            Nullázás
          </button>
        </div>

        <section className="setting-panel" aria-label="Idő beállítása">
          <div className="setting-header">
            <div>
              <p className="setting-label">Beállított idő</p>
              <strong className="setting-value">{formatClock(configuredSeconds)}</strong>
            </div>
            <span className="setting-hint">30 mp - 30 perc</span>
          </div>

          <input
            className="time-slider"
            type="range"
            min={MIN_SECONDS}
            max={MAX_SECONDS}
            step={30}
            value={configuredSeconds}
            onChange={(event) => updateConfiguredTime(Number(event.target.value))}
            aria-label="Visszaszámláló ideje"
          />
        </section>

        <footer className="footer-note">
          <p>0-nál hangjelzés indul, az idő pedig tovább fut, amíg újra nem indítod.</p>
          {!audioUnlocked ? <p>Az első gombnyomás engedélyezi a hangjelzést a böngészőben.</p> : null}
        </footer>
      </section>
    </main>
  );
}

export default App;
