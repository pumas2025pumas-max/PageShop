(() => {
  const canvas = document.getElementById('error-game-canvas');
  const startButton = document.getElementById('error-game-start');
  const scoreEl = document.getElementById('error-game-score');
  const bestEl = document.getElementById('error-game-best');
  const messageEl = document.getElementById('error-game-message');
  const yearEl = document.getElementById('error-year');
  const ctx = canvas ? canvas.getContext('2d') : null;

  if (yearEl) {
    yearEl.textContent = new Date().getFullYear().toString();
  }

  if (!canvas || !ctx) {
    return;
  }

  const STORAGE_KEY = 'petitReve404BestScore';
  const getBestFromStorage = () => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      return raw ? Number.parseInt(raw, 10) || 0 : 0;
    } catch (error) {
      return 0;
    }
  };

  const setBestInStorage = (value) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(value));
    } catch (error) {
      /* noop */
    }
  };

  const groundY = canvas.height - 50;
  const player = {
    width: 58,
    height: 52,
    x: 110,
    y: groundY - 52,
    vy: 0
  };

  const state = {
    playing: false,
    obstacles: [],
    decorations: [],
    score: 0,
    best: getBestFromStorage(),
    lastTime: 0,
    nextSpawn: 0,
    speed: 260
  };

  const randomBetween = (min, max) => Math.random() * (max - min) + min;

  const createDecoration = () => ({
    x: canvas.width + randomBetween(0, 200),
    y: randomBetween(40, 120),
    speed: randomBetween(22, 40),
    scale: randomBetween(0.7, 1.3)
  });

  const resetPlayer = () => {
    player.vy = 0;
    player.y = groundY - player.height;
  };

  const scheduleNextSpawn = () => {
    state.nextSpawn = randomBetween(0.9, 1.6);
  };

  const setMessage = (text, tone = 'neutral') => {
    if (!messageEl) return;
    messageEl.textContent = text;
    messageEl.className = `error-game__message error-game__message--${tone}`;
  };

  const updateScoreDisplay = () => {
    if (scoreEl) {
      scoreEl.textContent = Math.floor(state.score).toString();
    }
    if (bestEl) {
      bestEl.textContent = Math.floor(state.best).toString();
    }
  };

  const resetGame = () => {
    state.playing = false;
    state.obstacles = [];
    state.decorations = Array.from({ length: 3 }, createDecoration);
    state.score = 0;
    state.lastTime = 0;
    scheduleNextSpawn();
    resetPlayer();
    updateScoreDisplay();
    setMessage('Tocá "Comenzar a jugar" o presioná salto para empezar.');
    drawScene(0);
  };

  const spawnObstacle = () => {
    const height = randomBetween(36, 64);
    const width = randomBetween(28, 46);
    state.obstacles.push({
      x: canvas.width + 10,
      y: groundY - height,
      width,
      height,
      colorShift: Math.random()
    });
  };

  const startGame = () => {
    if (state.playing) return;
    state.playing = true;
    state.score = 0;
    state.obstacles = [];
    state.decorations = Array.from({ length: 3 }, createDecoration);
    state.lastTime = 0;
    scheduleNextSpawn();
    resetPlayer();
    setMessage('¡A saltar! Evitá las cajas de telas.');
  };

  const endGame = () => {
    state.playing = false;
    if (state.score > state.best) {
      state.best = state.score;
      setBestInStorage(Math.floor(state.best));
      setMessage(`Nuevo récord: ${Math.floor(state.score)} puntos. ¡Increíble!`, 'success');
    } else {
      setMessage(`¡Ups! Llegaste a ${Math.floor(state.score)} puntos. Probá otra vez.`, 'info');
    }
    updateScoreDisplay();
  };

  const jump = () => {
    if (!state.playing) {
      startGame();
    }
    const onGround = player.y >= groundY - player.height - 1;
    if (onGround) {
      player.vy = -420;
    }
  };

  const isColliding = (rect) => {
    return (
      player.x < rect.x + rect.width &&
      player.x + player.width > rect.x &&
      player.y < rect.y + rect.height &&
      player.y + player.height > rect.y
    );
  };

  const drawRoundedRect = (x, y, width, height, radius) => {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();
  };

  const drawCloud = (x, y, scale) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(scale, scale);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.beginPath();
    ctx.arc(-20, 0, 18, Math.PI * 0.5, Math.PI * 1.5);
    ctx.arc(0, -18, 22, Math.PI, Math.PI * 1.85);
    ctx.arc(28, -8, 16, Math.PI * 1.2, Math.PI * 1.9);
    ctx.arc(30, 6, 20, Math.PI * 1.5, Math.PI * 0.5, true);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  };

  const drawPlayer = () => {
    ctx.save();
    ctx.translate(player.x, player.y);
    ctx.fillStyle = '#f7cfe0';
    drawRoundedRect(0, 4, player.width, player.height - 4, 18);
    ctx.fillStyle = '#ffffff';
    drawRoundedRect(16, 0, 26, 24, 10);
    ctx.fillStyle = '#44313c';
    ctx.beginPath();
    ctx.arc(26, 10, 3, 0, Math.PI * 2);
    ctx.arc(34, 10, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillRect(25, 18, 12, 3);
    ctx.fillStyle = '#f2b6d1';
    drawRoundedRect(10, player.height - 14, 18, 14, 6);
    drawRoundedRect(player.width - 28, player.height - 14, 18, 14, 6);
    ctx.restore();
  };

  const drawObstacle = (obstacle) => {
    const { x, y, width, height, colorShift } = obstacle;
    const hue = 330 + colorShift * 40;
    ctx.fillStyle = `hsl(${hue}, 65%, 70%)`;
    drawRoundedRect(x, y, width, height, 8);
    ctx.fillStyle = `hsl(${hue}, 65%, 62%)`;
    ctx.fillRect(x + 6, y + height - 14, width - 12, 8);
  };

  const drawGround = () => {
    ctx.fillStyle = '#fbe9f2';
    ctx.fillRect(0, groundY, canvas.width, canvas.height - groundY);
    ctx.strokeStyle = '#f2b6d1';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, groundY);
    ctx.lineTo(canvas.width, groundY);
    ctx.stroke();
    ctx.lineWidth = 1;
    ctx.setLineDash([10, 14]);
    ctx.strokeStyle = 'rgba(68, 49, 60, 0.15)';
    ctx.beginPath();
    ctx.moveTo(0, groundY + 16);
    ctx.lineTo(canvas.width, groundY + 16);
    ctx.stroke();
    ctx.setLineDash([]);
  };

  const drawBackground = (time) => {
    ctx.fillStyle = '#fdf7fb';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, '#fdf7fb');
    gradient.addColorStop(1, '#f5eaf5');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    state.decorations.forEach((cloud) => {
      drawCloud(cloud.x, cloud.y, cloud.scale);
    });
  };

  const drawScene = (time) => {
    drawBackground(time);
    drawGround();
    state.obstacles.forEach(drawObstacle);
    drawPlayer();
  };

  const update = (time) => {
    const now = time || performance.now();
    let delta = 0;
    if (state.lastTime) {
      delta = (now - state.lastTime) / 1000;
      if (delta > 0.05) {
        delta = 0.05;
      }
    }
    state.lastTime = now;

    if (state.playing) {
      state.score += delta * 60;
      updateScoreDisplay();

      player.vy += 1200 * delta;
      player.y += player.vy * delta;
      if (player.y > groundY - player.height) {
        player.y = groundY - player.height;
        player.vy = 0;
      }

      state.obstacles.forEach((obstacle) => {
        obstacle.x -= state.speed * delta;
      });
      state.obstacles = state.obstacles.filter((obstacle) => obstacle.x + obstacle.width > -5);

      state.decorations.forEach((cloud, index) => {
        cloud.x -= cloud.speed * delta;
        if (cloud.x < -80) {
          state.decorations[index] = createDecoration();
        }
      });

      state.nextSpawn -= delta;
      if (state.nextSpawn <= 0) {
        spawnObstacle();
        scheduleNextSpawn();
      }

      const hasCollision = state.obstacles.some(isColliding);
      if (hasCollision) {
        endGame();
      }
    }

    drawScene(now);
    window.requestAnimationFrame(update);
  };

  const handleKeydown = (event) => {
    if (['Space', 'ArrowUp', 'KeyW'].includes(event.code)) {
      event.preventDefault();
      jump();
    }
  };

  const handlePointer = (event) => {
    event.preventDefault();
    jump();
  };

  if (startButton) {
    startButton.addEventListener('click', startGame);
  }

  window.addEventListener('keydown', handleKeydown);
  canvas.addEventListener('pointerdown', handlePointer);
  canvas.addEventListener('touchstart', handlePointer);

  updateScoreDisplay();
  resetGame();
  window.requestAnimationFrame(update);
})();
