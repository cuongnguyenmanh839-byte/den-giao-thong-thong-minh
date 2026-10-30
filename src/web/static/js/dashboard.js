// ===================================================================
// dashboard.js – Điều khiển và hiển thị dữ liệu trực quan ngã tư
// ===================================================================
'use strict';

const DIRS = ['NORTH', 'SOUTH', 'EAST', 'WEST'];
const DIR_VN = {
  NORTH: 'BẮC (NORTH)',
  SOUTH: 'NAM (SOUTH)',
  EAST:  'ĐÔNG (EAST)',
  WEST:  'TÂY (WEST)'
};
const DIR_SHORT = {
  NORTH: 'BẮC',
  SOUTH: 'NAM',
  EAST:  'ĐÔNG',
  WEST:  'TÂY'
};
const COLOR_VN = {
  GREEN:  'ĐÈN XANH (CHO PHÉP ĐI)',
  YELLOW: 'ĐÈN VÀNG (GIẢM TỐC)',
  RED:    'ĐÈN ĐỎ (DỪNG LẠI)'
};
const MAX_CHART_POINTS = 25;

// ─── 1. Khởi tạo Biểu đồ Chart.js ─────────────────────────
const ctx = document.getElementById('chartVehicles').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: DIRS.map((d, i) => ({
      label: DIR_SHORT[d],
      data: [],
      borderColor: ['#22c55e', '#eab308', '#3b82f6', '#ec4899'][i],
      backgroundColor: [
        'rgba(34, 197, 94, 0.1)',
        'rgba(234, 179, 8, 0.1)',
        'rgba(59, 130, 246, 0.1)',
        'rgba(236, 72, 153, 0.1)'
      ][i],
      tension: 0.35,
      fill: true,
      pointRadius: 2,
      borderWidth: 2
    }))
  },
  options: {
    responsive: true,
    animation: { duration: 250 },
    scales: {
      x: {
        ticks: { color: '#64748b', font: { size: 9 } },
        grid: { color: '#1e293b' }
      },
      y: {
        beginAtZero: true,
        ticks: { color: '#64748b', font: { size: 9 }, stepSize: 1 },
        grid: { color: '#1e293b' },
        title: { display: true, text: 'Số xe', color: '#64748b', font: { size: 9 } }
      }
    },
    plugins: {
      legend: {
        labels: { color: '#94a3b8', font: { size: 10, weight: 'bold' }, boxWidth: 10 }
      }
    }
  }
});

function addChartPoint(label, counts) {
  if (chart.data.labels.length >= MAX_CHART_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets.forEach(ds => ds.data.shift());
  }
  chart.data.labels.push(label);
  DIRS.forEach((d, i) => chart.data.datasets[i].data.push(counts[d] || 0));
  chart.update('none');
}

// ─── 2. Đồng hồ thời gian thực ───────────────────────────
function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('vi-VN');
}
setInterval(updateClock, 1000);
updateClock();

// ─── 3. Cập nhật đèn và hiệu ứng luồng xe tại ngã tư ───────
function updateLightsAndFlow(gpioState, activeDir, activeColor, remaining) {
  if (gpioState) trafficSim.gpioState = gpioState;
  DIRS.forEach(dir => {
    const isThisDirActive = (dir === activeDir);
    const flowEl = document.getElementById('flow-' + dir);
    const badgeEl = document.getElementById('badge-' + dir);

    // Bật/tắt đèn giao thông trên bản đồ SVG (dùng setAttribute cho SVGCircleElement)
    ['RED', 'YELLOW', 'GREEN'].forEach(color => {
      const lamp = document.getElementById(`${dir}-${color}`);
      if (!lamp) return;
      const lower = color.toLowerCase();
      const isLit = Boolean(gpioState && gpioState[dir] && gpioState[dir][color]);

      lamp.setAttribute('class', `visor-lamp ${lower}${isLit ? ' active-' + lower : ''}`);

      if (isLit) {
        if (color === 'RED') {
          lamp.setAttribute('fill', '#ff2e2e');
          lamp.setAttribute('stroke', '#fecaca');
          lamp.setAttribute('stroke-width', '2.2');
          lamp.setAttribute('filter', 'url(#glow-red)');
        } else if (color === 'YELLOW') {
          lamp.setAttribute('fill', '#fbbf24');
          lamp.setAttribute('stroke', '#fef08a');
          lamp.setAttribute('stroke-width', '2.2');
          lamp.setAttribute('filter', 'url(#glow-yellow)');
        } else if (color === 'GREEN') {
          lamp.setAttribute('fill', '#00f59b');
          lamp.setAttribute('stroke', '#a7f3d0');
          lamp.setAttribute('stroke-width', '2.2');
          lamp.setAttribute('filter', 'url(#glow-green)');
        }
      } else {
        lamp.removeAttribute('filter');
        lamp.setAttribute('stroke-width', '1.5');
        if (color === 'RED') {
          lamp.setAttribute('fill', '#2d1212');
          lamp.setAttribute('stroke', '#4a1515');
        } else if (color === 'YELLOW') {
          lamp.setAttribute('fill', '#2d2212');
          lamp.setAttribute('stroke', '#4a3715');
        } else if (color === 'GREEN') {
          lamp.setAttribute('fill', '#122d1f');
          lamp.setAttribute('stroke', '#154a2a');
        }
      }

      // Đồng bộ trạng thái sang mảng ledStates & nút bấm thủ công
      if (typeof ledStates !== 'undefined' && ledStates[dir]) {
        ledStates[dir][color] = isLit;
      }
      const mBtn = document.getElementById(`btn-${dir}-${color}`);
      if (mBtn) {
        mBtn.classList.toggle('active', isLit);
      }
    });

    // Cập nhật nhãn trạng thái trên bảng điện tử cạnh cột đèn
    const dirGreen  = Boolean(gpioState && gpioState[dir] && gpioState[dir].GREEN);
    const dirYellow = Boolean(gpioState && gpioState[dir] && gpioState[dir].YELLOW);

    if (dirGreen) {
      if (badgeEl) {
        badgeEl.textContent = isThisDirActive && remaining != null ? `ĐÈN XANH (${remaining}s)` : 'ĐÈN XANH (ĐI)';
        badgeEl.setAttribute('fill', '#34d399');
      }
      if (flowEl) flowEl.classList.add('flowing');
    } else if (dirYellow) {
      if (badgeEl) {
        badgeEl.textContent = isThisDirActive && remaining != null ? `ĐÈN VÀNG (${remaining}s)` : 'CHờ ĐỔI PHA';
        badgeEl.setAttribute('fill', '#fbbf24');
      }
      if (flowEl) flowEl.classList.remove('flowing');
    } else {
      if (badgeEl) {
        badgeEl.textContent = 'ĐÈN ĐỎ (DỪNG)';
        badgeEl.setAttribute('fill', '#f87171');
      }
      if (flowEl) flowEl.classList.remove('flowing');
    }
  });
}

// ─── 3b. Hệ thống mô phỏng Ô tô, Xe tải & Xe máy chuyển động 60 FPS ──
const SVG_CAR_COLORS = [
  { body: '#dc2626', stroke: '#f87171', roof: '#991b1b' }, // Đỏ thể thao
  { body: '#2563eb', stroke: '#60a5fa', roof: '#1d4ed8' }, // Xanh dương
  { body: '#f1f5f9', stroke: '#ffffff', roof: '#cbd5e1' }, // Trắng ngọc trai
  { body: '#eab308', stroke: '#fde047', roof: '#ca8a04', taxi: true }, // Vàng Taxi
  { body: '#059669', stroke: '#34d399', roof: '#047857' }, // Xanh lục điện (VF)
  { body: '#475569', stroke: '#94a3b8', roof: '#334155' }  // Xám kim loại
];

const HELMET_COLORS = ['#38bdf8', '#f43f5e', '#10b981', '#facc15', '#a855f7', '#fb923c'];
const BIKE_COLORS   = ['#ef4444', '#3b82f6', '#e2e8f0', '#14b8a6', '#f59e0b'];

// Trạng thái toàn cục cho bộ mô phỏng vật lý 60 FPS
const trafficSim = {
  activeDir: 'EAST',
  activeColor: 'GREEN',
  gpioState: {},
  targetCounts: { NORTH: 2, SOUTH: 2, EAST: 3, WEST: 2 },
  vehicles: { NORTH: [], SOUTH: [], EAST: [], WEST: [] },
  nextId: 1,
  lastTime: performance.now()
};

// Cấu hình 3 làn nhỏ (tracks) cho mỗi hướng:
// Track 0: Làn sát tim đường dành cho Ô tô / Xe tải / Bus
// Track 1: Làn giữa dành cho Ô tô & Xe máy
// Track 2: Làn sát vỉa hè chuyên cho Xe máy chạy song song
const DIR_GEOMETRY = {
  NORTH: {
    rot: 180,
    tracks: [272, 240, 214], // Tọa độ X cố định, đi theo chiều +Y (từ 0 -> 600)
    getXY: (s, trackX) => ({ x: trackX, y: s })
  },
  SOUTH: {
    rot: 0,
    tracks: [328, 360, 386], // Tọa độ X cố định, đi theo chiều -Y (từ 600 -> 0)
    getXY: (s, trackX) => ({ x: trackX, y: 600 - s })
  },
  WEST: {
    rot: 90,
    tracks: [328, 360, 386], // Tọa độ Y cố định, đi theo chiều +X (từ 0 -> 600)
    getXY: (s, trackY) => ({ x: s, y: trackY })
  },
  EAST: {
    rot: 270,
    tracks: [272, 240, 214], // Tọa độ Y cố định, đi theo chiều -X (từ 600 -> 0)
    getXY: (s, trackY) => ({ x: 600 - s, y: trackY })
  }
};

const STOP_LINE_S = 158; // Vị trí vạch dừng trắng tính theo trục hành trình s (0 -> 600)

function isDirectionGreen(dir) {
  if (trafficSim.gpioState && trafficSim.gpioState[dir]) {
    return Boolean(trafficSim.gpioState[dir].GREEN);
  }
  return (trafficSim.activeDir === dir && trafficSim.activeColor === 'GREEN');
}

function isDirectionYellow(dir) {
  if (trafficSim.gpioState && trafficSim.gpioState[dir]) {
    return Boolean(trafficSim.gpioState[dir].YELLOW);
  }
  return (trafficSim.activeDir === dir && trafficSim.activeColor === 'YELLOW');
}

function createVehicle(dir, forceTrack = null, initialS = null) {
  // Chọn track (0: Ô tô/Tải, 1: Hỗn hợp, 2: Xe máy)
  const trackIdx = forceTrack !== null ? forceTrack : (Math.random() < 0.45 ? 2 : (Math.random() < 0.55 ? 0 : 1));
  let type = 'car';
  if (trackIdx === 2) {
    type = 'motorbike';
  } else if (trackIdx === 1) {
    type = Math.random() < 0.55 ? 'motorbike' : 'car';
  } else {
    type = Math.random() < 0.22 ? 'truck' : 'car';
  }

  const halfLen = type === 'truck' ? 25 : (type === 'car' ? 20 : 12);
  const maxSpeed = type === 'motorbike'
    ? (115 + Math.random() * 28)   // px/giây
    : (type === 'truck' ? (88 + Math.random() * 15) : (102 + Math.random() * 22));

  // Tìm phương tiện cuối hàng trong cùng track để không đè lên nhau khi spawn
  const sameTrack = trafficSim.vehicles[dir].filter(v => v.trackIdx === trackIdx);
  let minS = Infinity;
  sameTrack.forEach(v => {
    if (v.s - v.halfLen < minS) minS = v.s - v.halfLen;
  });

  const spawnS = initialS !== null
    ? initialS
    : Math.min(-35 - Math.random() * 35, minS - halfLen - 22);

  // Không spawn quá xa ngoài màn hình nếu hàng chờ đã quá dài
  if (spawnS < -260) return null;

  const id = trafficSim.nextId++;
  const colorObj = SVG_CAR_COLORS[id % SVG_CAR_COLORS.length];
  const bikeColor = BIKE_COLORS[id % BIKE_COLORS.length];
  const helmetColor = HELMET_COLORS[(id * 3) % HELMET_COLORS.length];

  const v = {
    id,
    dir,
    type,
    trackIdx,
    s: spawnS,
    halfLen,
    speed: maxSpeed * 0.7,
    maxSpeed,
    accel: type === 'motorbike' ? 190 : 145,
    decel: type === 'motorbike' ? 280 : 230,
    braking: false,
    colorObj,
    bikeColor,
    helmetColor,
    lateralJitter: type === 'motorbike' ? (Math.random() * 4 - 2) : 0
  };
  trafficSim.vehicles[dir].push(v);
  return v;
}

function renderVehicleSVG(v) {
  const geom = DIR_GEOMETRY[v.dir];
  const laneCoord = geom.tracks[v.trackIdx] + v.lateralJitter;
  const pos = geom.getXY(v.s, laneCoord);
  const brakeGlow = v.braking ? '#ff1e1e' : '#dc2626';
  const brakeRadius = v.braking ? 3.2 : 2.1;

  if (v.type === 'motorbike') {
    return `
      <g class="svg-vehicle svg-motorbike" transform="translate(${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}) rotate(${geom.rot})">
        <!-- Chùm đèn pha xe máy -->
        <polygon points="-3,-11 -11,-48 11,-48 3,-11" fill="url(#headlight-beam)" opacity="0.65"/>
        <!-- Bóng đổ -->
        <ellipse cx="0" cy="0" rx="5.5" ry="12" fill="#000000" opacity="0.45"/>
        <!-- Bánh trước & dè trước -->
        <rect x="-1.8" y="-12.5" width="3.6" height="6" rx="1.5" fill="#0f172a"/>
        <rect x="-2.5" y="-9.5" width="5" height="4.5" rx="2" fill="${v.bikeColor}"/>
        <!-- Tay lái & Gương chiếu hậu -->
        <line x1="-6.5" y1="-5.5" x2="6.5" y2="-5.5" stroke="#cbd5e1" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="-7" cy="-6.2" r="1.2" fill="#94a3b8"/>
        <circle cx="7" cy="-6.2" r="1.2" fill="#94a3b8"/>
        <!-- Thân xe tay ga -->
        <rect x="-4" y="-6.5" width="8" height="16" rx="3.5" fill="${v.bikeColor}" stroke="#ffffff" stroke-opacity="0.4" stroke-width="0.8"/>
        <!-- Yên xe & Người lái đội mũ bảo hiểm -->
        <ellipse cx="0" cy="1.5" rx="4.8" ry="3.8" fill="#1e293b"/>
        <circle cx="0" cy="-1" r="4.2" fill="${v.helmetColor}" stroke="#0f172a" stroke-width="1"/>
        <!-- Kính mũ bảo hiểm -->
        <path d="M -3,-3 Q 0,-5 3,-3" stroke="#e2e8f0" stroke-width="1.2" fill="none"/>
        <!-- Đèn pha trước & Đèn hậu phanh -->
        <circle cx="0" cy="-10.5" r="2" fill="#fef08a"/>
        <circle cx="0" cy="10" r="${v.braking ? 2.6 : 1.7}" fill="${brakeGlow}"/>
      </g>
    `;
  }

  if (v.type === 'truck') {
    return `
      <g class="svg-vehicle svg-truck" transform="translate(${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}) rotate(${geom.rot})">
        <!-- Chùm sáng đèn pha đôi -->
        <polygon points="-9,-25 -24,-85 24,-85 9,-25" fill="url(#headlight-beam)" opacity="0.7"/>
        <!-- Bóng đổ -->
        <rect x="-14" y="-24" width="28" height="50" rx="5" fill="#000000" opacity="0.45"/>
        <!-- Bánh xe tải -->
        <rect x="-14.5" y="-19" width="4" height="9" rx="1.5" fill="#090d16"/>
        <rect x="10.5" y="-19" width="4" height="9" rx="1.5" fill="#090d16"/>
        <rect x="-14.5" y="11" width="4" height="9" rx="1.5" fill="#090d16"/>
        <rect x="10.5" y="11" width="4" height="9" rx="1.5" fill="#090d16"/>
        <!-- Đầu cabin xe tải -->
        <rect x="-11.5" y="-25" width="23" height="16" rx="4" fill="#3b82f6" stroke="#93c5fd" stroke-width="1.2"/>
        <!-- Kính chắn gió cabin -->
        <rect x="-9" y="-21" width="18" height="6.5" rx="1.5" fill="#38bdf8" fill-opacity="0.9"/>
        <!-- Thùng hàng phía sau -->
        <rect x="-12" y="-8" width="24" height="32" rx="3" fill="#e2e8f0" stroke="#94a3b8" stroke-width="1.5"/>
        <line x1="-11" y1="2" x2="11" y2="2" stroke="#cbd5e1" stroke-width="1"/>
        <line x1="-11" y1="12" x2="11" y2="12" stroke="#cbd5e1" stroke-width="1"/>
        <!-- Đèn pha & Đèn phanh -->
        <circle cx="-8" cy="-24.5" r="2.6" fill="#fef08a"/>
        <circle cx="8" cy="-24.5" r="2.6" fill="#fef08a"/>
        <rect x="-9.5" y="23" width="5" height="2.5" rx="1" fill="${brakeGlow}"/>
        <rect x="4.5" y="23" width="5" height="2.5" rx="1" fill="${brakeGlow}"/>
      </g>
    `;
  }

  // Mặc định: Ô tô con (Sedan / Taxi)
  const col = v.colorObj;
  const taxiSign = col.taxi
    ? `<rect x="-4.5" y="-4" width="9" height="3.5" rx="1" fill="#fef08a" stroke="#ca8a04" stroke-width="0.6"/>`
    : '';
  return `
    <g class="svg-vehicle svg-car" transform="translate(${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}) rotate(${geom.rot})">
      <!-- Quầng sáng đèn pha -->
      <polygon points="-8,-20 -22,-78 22,-78 8,-20" fill="url(#headlight-beam)" opacity="0.68"/>
      <!-- Bóng đổ gầm xe -->
      <rect x="-13.5" y="-19" width="27" height="40" rx="6" fill="#000000" opacity="0.42"/>
      <!-- 4 Bánh xe -->
      <rect x="-13.5" y="-16" width="4" height="8" rx="1.5" fill="#090d16"/>
      <rect x="9.5" y="-16" width="4" height="8" rx="1.5" fill="#090d16"/>
      <rect x="-13.5" y="9" width="4" height="8" rx="1.5" fill="#090d16"/>
      <rect x="9.5" y="9" width="4" height="8" rx="1.5" fill="#090d16"/>
      <!-- Gương chiếu hậu -->
      <rect x="-14.5" y="-12" width="3.5" height="4" rx="1.2" fill="${col.stroke}"/>
      <rect x="11" y="-12" width="3.5" height="4" rx="1.2" fill="${col.stroke}"/>
      <!-- Thân xe ô tô -->
      <rect x="-11" y="-20" width="22" height="40" rx="5.5" fill="${col.body}" stroke="${col.stroke}" stroke-width="1.3"/>
      <!-- Kính chắn gió trước -->
      <rect x="-8" y="-12" width="16" height="7" rx="2" fill="#38bdf8" fill-opacity="0.88"/>
      <!-- Nóc xe -->
      <rect x="-7.5" y="-3.5" width="15" height="11" rx="2.5" fill="${col.roof}" stroke="${col.stroke}" stroke-opacity="0.4" stroke-width="0.8"/>
      ${taxiSign}
      <!-- Kính sau -->
      <rect x="-7.5" y="9.5" width="15" height="4.5" rx="1.5" fill="#0f172a" fill-opacity="0.8"/>
      <!-- Đèn pha LED trước -->
      <circle cx="-7.5" cy="-19.2" r="2.4" fill="#fef08a"/>
      <circle cx="7.5" cy="-19.2" r="2.4" fill="#fef08a"/>
      <!-- Đèn phanh hậu -->
      <circle cx="-7.5" cy="19.2" r="${brakeRadius}" fill="${brakeGlow}"/>
      <circle cx="7.5" cy="19.2" r="${brakeRadius}" fill="${brakeGlow}"/>
    </g>
  `;
}

// Khởi tạo sẵn một số xe ban đầu trên 4 hướng để giao lộ luôn sống động ngay khi mở trang
function initTrafficSim() {
  DIRS.forEach(dir => {
    createVehicle(dir, 0, 95);
    createVehicle(dir, 2, 110);
    createVehicle(dir, 1, 45);
    createVehicle(dir, 2, 55);
  });
}

function stepTrafficPhysics(now) {
  const dt = Math.min(0.05, Math.max(0.005, (now - trafficSim.lastTime) / 1000));
  trafficSim.lastTime = now;

  DIRS.forEach(dir => {
    const green = isDirectionGreen(dir);
    const yellow = isDirectionYellow(dir);
    const list = trafficSim.vehicles[dir];

    // Số lượng xe mục tiêu trên mỗi hướng: luôn có tối thiểu 3-5 phương tiện (ô tô + xe máy)
    // và tăng lên khi camera hoặc bộ giả lập báo nhiều xe
    const rawCount = (trafficSim.targetCounts && trafficSim.targetCounts[dir]) || 0;
    const desiredCount = Math.min(12, Math.max(green ? 5 : 4, rawCount + 3));

    if (list.length < desiredCount && Math.random() < (green ? 0.12 : 0.08)) {
      createVehicle(dir);
    }

    // Cập nhật từng track độc lập để xe máy & ô tô đi song song nhiều làn
    [0, 1, 2].forEach(trackIdx => {
      const trackVehicles = list
        .filter(v => v.trackIdx === trackIdx)
        .sort((a, b) => b.s - a.s); // Xe đi đầu (s lớn nhất) xếp trước

      for (let i = 0; i < trackVehicles.length; i++) {
        const v = trackVehicles[i];
        const leader = i > 0 ? trackVehicles[i - 1] : null;
        const frontBumper = v.s + v.halfLen;

        // 1. Tính chướng ngại vật phía trước (xe đi trước trong cùng làn)
        let maxAllowedFront = Infinity;
        if (leader) {
          const safeGap = v.type === 'motorbike' ? 9 : 13;
          maxAllowedFront = (leader.s - leader.halfLen) - safeGap;
        }

        // 2. Nếu đèn ĐỎ (hoặc VÀNG và xe còn ở trước vạch dừng), phải dừng trước vạch trắng
        if (!green) {
          // Chỉ dừng nếu đầu xe chưa vượt qua vạch dừng
          const stopThreshold = yellow ? STOP_LINE_S - 8 : STOP_LINE_S + 4;
          if (frontBumper <= stopThreshold) {
            maxAllowedFront = Math.min(maxAllowedFront, STOP_LINE_S);
          }
        }

        const distToObstacle = maxAllowedFront - frontBumper;

        // 3. Điều khiển gia tốc / phanh mượt mà
        if (distToObstacle <= 1.5) {
          v.speed = 0;
          v.braking = true;
          if (distToObstacle < 0 && leader) {
            v.s = maxAllowedFront - v.halfLen;
          }
        } else if (distToObstacle < 48) {
          // Giảm tốc dần khi tiến gần vạch dừng hoặc xe phía trước
          const targetSpd = Math.max(0, v.maxSpeed * (distToObstacle / 48) * 0.65);
          if (v.speed > targetSpd) {
            v.speed = Math.max(0, v.speed - v.decel * dt);
            v.braking = true;
          } else {
            v.speed = Math.min(v.maxSpeed, v.speed + v.accel * 0.5 * dt);
            v.braking = false;
          }
        } else {
          // Đường thoáng hoặc đèn XANH -> Tăng tốc qua ngã tư
          v.speed = Math.min(v.maxSpeed, v.speed + v.accel * dt);
          v.braking = false;
        }

        v.s += v.speed * dt;
      }
    });

    // Xóa các xe đã chạy thoát khỏi bản đồ (s > 650)
    trafficSim.vehicles[dir] = list.filter(v => v.s < 650);

    // Render SVG cho hướng này
    const laneEl = document.getElementById('cars-' + dir);
    if (laneEl) {
      // Sắp xếp theo s để vẽ xe hợp lý
      laneEl.innerHTML = trafficSim.vehicles[dir]
        .map(v => renderVehicleSVG(v))
        .join('');
    }
  });

  requestAnimationFrame(stepTrafficPhysics);
}

function updateCarsOnLanes(counts, activeDir, activeColor) {
  if (counts) {
    DIRS.forEach(d => {
      trafficSim.targetCounts[d] = Number(counts[d] || 0);
    });
  }
  if (activeDir) trafficSim.activeDir = activeDir;
  if (activeColor) trafficSim.activeColor = activeColor;
}

initTrafficSim();
requestAnimationFrame(stepTrafficPhysics);

// ─── 4. Cập nhật thanh mật độ xe ─────────────────────────
function updateDensity(counts, levels, waitTimes) {
  DIRS.forEach(dir => {
    const cnt = counts[dir] || 0;
    const lv  = levels[dir] || 'LOW';
    const wt  = waitTimes && waitTimes[dir] != null ? Math.round(waitTimes[dir]) : 0;

    // Chip số xe gắn trên nhánh đường ngã tư
    const armChip = document.getElementById('cnt-' + dir);
    if (armChip) armChip.textContent = `🚗 ${cnt} xe`;

    // Thẻ mật độ chi tiết phía dưới
    const qtyEl = document.getElementById('qty-' + dir);
    if (qtyEl) qtyEl.textContent = `${cnt} xe`;

    const barEl = document.getElementById('bar-' + dir);
    if (barEl) {
      const pct = Math.min(100, Math.max(10, cnt * 20));
      barEl.style.width = pct + '%';
      barEl.className = 'den-meter-fill' + (lv === 'HIGH' ? ' high' : lv === 'MEDIUM' ? ' medium' : '');
    }

    const lvEl = document.getElementById('lv-' + dir);
    if (lvEl) {
      const lvVN = { LOW: 'Thông thoáng', MEDIUM: 'Vừa phải', HIGH: 'Đông xe (Ưu tiên)' };
      lvEl.textContent = lvVN[lv] || lv;
      lvEl.className = 'den-status-chip ' + (lv === 'HIGH' ? 'high' : lv === 'MEDIUM' ? 'medium' : 'low');
    }

    const wtEl = document.getElementById('wt-sub-' + dir);
    if (wtEl) wtEl.textContent = `Đã chờ: ${wt}s`;
  });
}

// ─── 5. Cập nhật trạng thái tổng thể và banner to ─────────
let lastPhaseCount = 0;

function updateStatus(data) {
  const activeDir = data.active_dir || 'NORTH';
  const activeColor = data.active_color || 'RED';
  const remaining = data.time_remaining != null ? data.time_remaining : 0;

  // Cập nhật Header & Băng thông báo to trên đầu giao lộ
  const banner = document.getElementById('flow-banner');
  const bannerTitle = document.getElementById('banner-title');
  const bannerCountdown = document.getElementById('banner-countdown');
  const bannerDot = document.getElementById('banner-dot');

  if (activeColor === 'GREEN') {
    banner.className = 'flow-banner state-green';
    bannerDot.textContent = '🟢';
    bannerTitle.textContent = `${DIR_VN[activeDir]} ĐƯỢC ĐI`;
    bannerCountdown.style.color = '#10b981';
  } else if (activeColor === 'YELLOW') {
    banner.className = 'flow-banner state-yellow';
    bannerDot.textContent = '🟡';
    bannerTitle.textContent = `${DIR_VN[activeDir]} SẮP ĐỔI ĐÈN`;
    bannerCountdown.style.color = '#f59e0b';
  } else {
    banner.className = 'flow-banner state-red';
    bannerDot.textContent = '🔴';
    bannerTitle.textContent = 'TOÀN BỘ GIAO LỘ DỪNG (AN TOÀN)';
    bannerCountdown.style.color = '#ef4444';
  }
  bannerCountdown.innerHTML = `${remaining}<small>s</small>`;

  // Cập nhật KPI Strip trên cùng
  const kpiDir = document.getElementById('kpi-active-dir');
  const kpiState = document.getElementById('kpi-active-state');
  const kpiCd = document.getElementById('kpi-countdown');
  const kpiHw = document.getElementById('kpi-hw-status');
  const kpiHwSub = document.getElementById('kpi-hw-sub');
  const hdrPort = document.getElementById('hdr-port-code');

  if (kpiDir) kpiDir.textContent = DIR_VN[activeDir] || activeDir;
  if (kpiState) {
    kpiState.textContent = COLOR_VN[activeColor] || activeColor;
    kpiState.style.color = activeColor === 'GREEN' ? '#34d399' : activeColor === 'YELLOW' ? '#fbbf24' : '#f87171';
  }
  if (kpiCd) {
    kpiCd.textContent = `${remaining}s`;
    kpiCd.style.color = activeColor === 'GREEN' ? '#10b981' : activeColor === 'YELLOW' ? '#f59e0b' : '#ef4444';
  }
  if (kpiHw) {
    kpiHw.textContent = data.gpio_sim ? 'CHẾ ĐỘ MÔ PHỎNG' : `UNO R3 (${data.serial_port || 'COM'})`;
    kpiHw.style.color = data.gpio_sim ? '#fbbf24' : '#34d399';
  }
  if (kpiHwSub) {
    kpiHwSub.textContent = data.lcd_ok
      ? '12 LED (Pin 2→13) • LCD 1602 (A4/A5) OK'
      : '12 LED (Pin 2→13) • LCD 1602 Chế độ ảo';
  }
  if (hdrPort && data.serial_port) {
    hdrPort.textContent = `COM ${data.serial_port} • Pin 2→13`;
  }

  // Cập nhật tâm HUB ngã tư
  const hubDir = document.getElementById('hub-active-dir');
  const hubCountdown = document.getElementById('hub-countdown');
  const hubStatus = document.getElementById('hub-status-txt');

  if (hubDir) hubDir.textContent = DIR_SHORT[activeDir] || '--';
  if (hubCountdown) hubCountdown.textContent = remaining + 's';
  if (activeColor === 'GREEN') {
    if (hubCountdown) hubCountdown.setAttribute('fill', '#10b981');
    if (hubStatus) {
      hubStatus.textContent = 'CHO PHÉP ĐI';
      hubStatus.setAttribute('fill', '#10b981');
    }
  } else if (activeColor === 'YELLOW') {
    if (hubCountdown) hubCountdown.setAttribute('fill', '#f59e0b');
    if (hubStatus) {
      hubStatus.textContent = 'ĐÈN VÀNG';
      hubStatus.setAttribute('fill', '#f59e0b');
    }
  } else {
    if (hubCountdown) hubCountdown.setAttribute('fill', '#ef4444');
    if (hubStatus) {
      hubStatus.textContent = 'DỪNG LẠI';
      hubStatus.setAttribute('fill', '#ef4444');
    }
  }

  // Header số pha
  document.getElementById('header-phase-num').textContent = data.phase_count || 1;
  document.getElementById('hw-phase').textContent = data.phase_count || 1;

  // Chế độ hoạt động
  const modeVN = {
    FIXED:    'Cố Định (Tuần tự 30s)',
    ADAPTIVE: 'Thông Minh AI (Theo mật độ xe)',
    SAFE:     'An Toàn (Dừng toàn bộ 4 hướng)',
    MANUAL:   'Thủ Công'
  };
  document.getElementById('mode-label').textContent = modeVN[data.mode] || data.mode;

  // Thẻ chế độ active
  ['fixed', 'adaptive', 'safe'].forEach(m => {
    const el = document.getElementById('btn-' + m);
    if (el) el.classList.toggle('active', data.mode === m.toUpperCase());
  });

  // Thông số kỹ thuật
  const hwGpio = document.getElementById('hw-gpio');
  if (hwGpio) {
    hwGpio.textContent = data.gpio_sim ? 'MÔ PHỎNG' : (data.serial_port || 'UNO ĐÃ NỐI');
    hwGpio.className = 'tag ' + (data.gpio_sim ? 'sim' : 'ok');
  }

  const hwLcd = document.getElementById('hw-lcd');
  if (hwLcd) {
    hwLcd.textContent = data.lcd_ok ? 'ĐÃ KẾT NỐI' : 'MÔ PHỎNG';
    hwLcd.className = 'tag ' + (data.lcd_ok ? 'ok' : 'sim');
  }

  // Cập nhật Màn hình LCD 16x2 trực tuyến
  renderVirtualLCD(data.lcd_text, data.lcd_ok, data.serial_port);

  // Thời gian chờ các hướng
  const wt = data.wait_times || {};
  const wtNS = document.getElementById('wt-NORTH-SOUTH');
  if (wtNS) wtNS.textContent = `${Math.round(wt.NORTH || 0)}s / ${Math.round(wt.SOUTH || 0)}s`;

  const wtEW = document.getElementById('wt-EAST-WEST');
  if (wtEW) wtEW.textContent = `${Math.round(wt.EAST || 0)}s / ${Math.round(wt.WEST || 0)}s`;

  // Cập nhật đèn và luồng giao thông
  if (data.gpio_state) {
    updateLightsAndFlow(data.gpio_state, activeDir, activeColor, remaining);
  }
  updateCarsOnLanes(data.vehicle_counts, activeDir, activeColor);

  // Log pha mới
  if (data.phase_count > lastPhaseCount && activeDir) {
    lastPhaseCount = data.phase_count;
    addPhaseLog(activeDir, activeColor, data.mode);
  }
}

function addPhaseLog(dir, color, mode) {
  const wrap = document.getElementById('phase-log');
  const empty = wrap.querySelector('.log-empty');
  if (empty) empty.remove();

  const t = new Date().toLocaleTimeString('vi-VN');
  const item = document.createElement('div');
  const cls = { GREEN: 'green', YELLOW: 'yellow', RED: 'red' }[color] || '';
  item.className = 'log-item ' + cls;
  item.innerHTML = `
    <span class="log-time">${t}</span>
    <span><strong>${DIR_VN[dir] || dir}</strong> → ${COLOR_VN[color] || color} [${mode}]</span>
  `;
  wrap.insertBefore(item, wrap.firstChild);
  while (wrap.children.length > 20) {
    wrap.removeChild(wrap.lastChild);
  }
}

// ─── 6. Polling dữ liệu tự động ───────────────────────────
let pollErrors = 0;

async function poll() {
  try {
    const [status, vision] = await Promise.all([
      fetch('/api/status').then(r => r.json()),
      fetch('/api/vision').then(r => r.json())
    ]);

    pollErrors = 0;
    const sysPill = document.getElementById('sys-status-text');
    if (sysPill) {
      sysPill.textContent = status.gpio_sim
        ? 'Pi 5 Online (Mô phỏng Uno)'
        : `Pi 5 ⇄ Uno (${status.serial_port || 'COM'})`;
    }

    const totalVeh = Object.values(vision.counts || {}).reduce((a, b) => a + (Number(b) || 0), 0);
    const kpiTotal = document.getElementById('kpi-total-vehicles');
    if (kpiTotal) kpiTotal.textContent = `${totalVeh} xe`;
    const kpiVisMode = document.getElementById('kpi-vision-mode');
    if (kpiVisMode) {
      kpiVisMode.textContent = vision.source_mode === 'MANUAL'
        ? 'Nguồn dữ liệu: Giả lập thủ công'
        : 'Nguồn dữ liệu: Nhận diện Camera AI';
    }

    updateStatus(status);
    updateDensity(vision.counts || {}, vision.density_levels || {}, status.wait_times || {});

    // Camera FPS & trạng thái
    const camFps = document.getElementById('cam-fps');
    if (camFps) camFps.textContent = `⚡ Tốc độ: ${vision.fps || 0} FPS`;

    const camOk = vision.camera_ok;
    const camOkEl = document.getElementById('cam-ok');
    if (camOkEl) camOkEl.textContent = `Trạng thái: ${camOk ? 'Đang nhận diện tốt' : 'Không có camera'}`;

    const hwCam = document.getElementById('hw-cam');
    if (hwCam) {
      hwCam.textContent = camOk ? 'SẴN SÀNG' : 'KHÔNG CÓ';
      hwCam.className = 'tag ' + (camOk ? 'ok' : 'sim');
    }

    // Chart
    const t = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    addChartPoint(t, vision.counts || {});

  } catch (e) {
    pollErrors++;
    if (pollErrors > 3) {
      const sysPill = document.getElementById('sys-status-text');
      if (sysPill) sysPill.textContent = 'Mất kết nối máy chủ';
    }
  }
}

// ─── 7. Chuyển đổi chế độ hoạt động ───────────────────────
async function setMode(mode) {
  try {
    await fetch('/api/set_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    });
    poll();
  } catch (e) {
    console.error('setMode error', e);
  }
}

// ─── 8. Kiểm tra thủ công từng đèn (bắt bệnh đứt dây) ────
let ledStates = {
  NORTH: { RED: false, YELLOW: false, GREEN: false },
  SOUTH: { RED: false, YELLOW: false, GREEN: false },
  EAST:  { RED: false, YELLOW: false, GREEN: false },
  WEST:  { RED: false, YELLOW: false, GREEN: false }
};

async function toggleLed(direction, color) {
  const current = ledStates[direction][color];
  const newState = !current;
  ledStates[direction][color] = newState;

  try {
    const res = await fetch('/api/manual/light', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ direction, color, state: newState })
    });
    const data = await res.json();
    if (data.gpio_state) {
      updateLightsAndFlow(data.gpio_state, null, null, 0);
    }
    const btn = document.getElementById(`btn-${direction}-${color}`);
    if (btn) btn.classList.toggle('active', newState);
  } catch (e) {
    console.error('toggleLed error', e);
  }
}

async function manualAll(turnOn) {
  DIRS.forEach(d => {
    ['RED', 'YELLOW', 'GREEN'].forEach(c => {
      ledStates[d][c] = turnOn;
      const btn = document.getElementById(`btn-${d}-${c}`);
      if (btn) btn.classList.toggle('active', turnOn);
    });
  });

  try {
    const res = await fetch('/api/manual/all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ turn_on: turnOn })
    });
    const data = await res.json();
    if (data.gpio_state) {
      updateLightsAndFlow(data.gpio_state, null, null, 0);
    }
  } catch (e) {
    console.error('manualAll error', e);
  }
}

async function manualSelfTest() {
  try {
    await fetch('/api/manual/self_test', { method: 'POST' });
  } catch (e) {
    console.error('manualSelfTest error', e);
  }
}

// ─── 9. Giả lập mật độ xe thủ công & Bật/tắt khung camera ─
let simCounts = { NORTH: 0, SOUTH: 0, EAST: 0, WEST: 0 };

async function toggleZones() {
  try {
    const res = await fetch('/api/vision/toggle_zones', { method: 'POST' });
    const data = await res.json();
    const btn = document.getElementById('btn-toggle-zones');
    if (btn) {
      btn.textContent = data.show_zones ? '👁️ Đang Hiện Khung' : '👁️ Bật/Tắt Khung';
    }
  } catch (e) {
    console.error('toggleZones error', e);
  }
}

async function adjustSimCount(dir, delta) {
  simCounts[dir] = Math.max(0, (simCounts[dir] || 0) + delta);
  document.getElementById(`sim-val-${dir}`).textContent = simCounts[dir];

  const badge = document.getElementById('source-badge');
  if (badge) {
    badge.textContent = 'ĐANG GIẢ LẬP';
    badge.style.background = 'rgba(245, 158, 11, 0.2)';
    badge.style.color = '#fbbf24';
  }

  try {
    await fetch('/api/vision/set_manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ counts: simCounts })
    });
    poll();
  } catch (e) {
    console.error('adjustSimCount error', e);
  }
}

async function applyPreset(type) {
  if (type === 'EAST_CONGESTION') {
    simCounts = { NORTH: 1, SOUTH: 0, EAST: 8, WEST: 1 };
  } else if (type === 'NORTH_CONGESTION') {
    simCounts = { NORTH: 9, SOUTH: 1, EAST: 1, WEST: 0 };
  } else if (type === 'CLEAR') {
    simCounts = { NORTH: 1, SOUTH: 1, EAST: 1, WEST: 1 };
  }

  DIRS.forEach(d => {
    const el = document.getElementById(`sim-val-${d}`);
    if (el) el.textContent = simCounts[d];
  });

  const badge = document.getElementById('source-badge');
  if (badge) {
    badge.textContent = 'ĐANG GIẢ LẬP';
    badge.style.background = 'rgba(245, 158, 11, 0.2)';
    badge.style.color = '#fbbf24';
  }

  try {
    await fetch('/api/vision/set_manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ counts: simCounts })
    });
    poll();
  } catch (e) {
    console.error('applyPreset error', e);
  }
}

async function switchSource(src) {
  try {
    await fetch('/api/vision/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: src })
    });
    const badge = document.getElementById('source-badge');
    if (badge) {
      badge.textContent = src === 'CAMERA' ? 'TỪ CAMERA' : 'TỰ DO CHỈNH';
      badge.style.background = src === 'CAMERA' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(59, 130, 246, 0.2)';
      badge.style.color = src === 'CAMERA' ? '#34d399' : '#60a5fa';
    }
    poll();
  } catch (e) {
    console.error('switchSource error', e);
  }
}

async function reconnectLcd() {
  const btn = document.getElementById('btn-lcd-reconnect');
  if (btn) btn.textContent = '⏳ Đang dò cổng COM (/dev/ttyACM*, /dev/ttyUSB*)...';
  try {
    const res = await fetch('/api/lcd/reconnect', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`✓ ĐÃ KẾT NỐI THÀNH CÔNG VỚI ARDUINO UNO R3!\nCổng COM: ${data.serial_port || '/dev/ttyACM0'}\n12 Đèn LED (Pin 2→13) và LCD 1602 (Pin A4/A5) đã sẵn sàng.`);
    } else {
      alert('⚠️ Chưa tìm thấy Arduino Uno R3 trên cổng USB COM (/dev/ttyACM0 hoặc /dev/ttyUSB0).\n\nBạn vui lòng kiểm tra:\n1. Đã cắm cáp USB từ Arduino Uno vào cổng USB của Raspberry Pi chưa.\n2. Đã nạp file arduino_uno_traffic.ino vào Arduino Uno chưa (Baudrate 115200).\n3. Màn hình LCD I2C cắm trên Arduino Uno: VCC->5V, GND->GND, SDA->A4, SCL->A5.');
    }
    poll();
  } catch (e) {
    console.error('reconnectLcd error', e);
  } finally {
    if (btn) btn.textContent = '🔄 Quét Cổng COM & Kết Nối Lại Arduino Uno';
  }
}

// ─── 10. Màn hình LCD 16x2 Trực Tuyến (Virtual LCD) ───────
function initLcdCells() {
  ['lcd-row-1', 'lcd-row-2'].forEach(rowId => {
    const rowEl = document.getElementById(rowId);
    if (!rowEl || rowEl.children.length === 16) return;
    rowEl.innerHTML = '';
    for (let i = 0; i < 16; i++) {
      const cell = document.createElement('div');
      cell.className = 'lcd-cell';
      cell.innerHTML = '&nbsp;';
      rowEl.appendChild(cell);
    }
  });
}

function renderVirtualLCD(lcdText, isHwOk, serialPort) {
  initLcdCells();
  const lines = Array.isArray(lcdText) ? lcdText : ['', ''];
  const l1 = (lines[0] || '').padEnd(16, ' ').slice(0, 16);
  const l2 = (lines[1] || '').padEnd(16, ' ').slice(0, 16);

  const row1 = document.getElementById('lcd-row-1');
  const row2 = document.getElementById('lcd-row-2');
  if (row1 && row1.children.length === 16) {
    for (let i = 0; i < 16; i++) {
      const ch = l1[i];
      row1.children[i].innerHTML = (ch === ' ' ? '&nbsp;' : ch);
    }
  }
  if (row2 && row2.children.length === 16) {
    for (let i = 0; i < 16; i++) {
      const ch = l2[i];
      row2.children[i].innerHTML = (ch === ' ' ? '&nbsp;' : ch);
    }
  }

  const badge = document.getElementById('badge-lcd-hw');
  const msg = document.getElementById('lcd-diag-msg');
  if (badge) {
    badge.textContent = isHwOk ? `UNO (${serialPort || 'COM'})` : 'CHẾ ĐỘ ẢO';
    badge.className = 'badge badge-lcd-hw ' + (isHwOk ? 'connected' : '');
  }
  if (msg) {
    if (isHwOk) {
      msg.textContent = `✓ Đang kết nối Arduino Uno R3 qua ${serialPort || 'cổng COM'} (12 LED: Pin 2→13 | LCD I2C: A4/A5).`;
      msg.className = 'lcd-status-msg ok';
    } else {
      msg.textContent = '⚠️ Chưa cắm cáp USB Arduino Uno (/dev/ttyACM0, /dev/ttyUSB0). Đang chạy mô phỏng trực tuyến trên Web.';
      msg.className = 'lcd-status-msg';
    }
  }
}

function setLcdTheme(theme) {
  const glass = document.getElementById('lcd-glass');
  const btnBlue = document.getElementById('btn-lcd-blue');
  const btnGreen = document.getElementById('btn-lcd-green');
  if (!glass) return;

  if (theme === 'green') {
    glass.className = 'lcd-glass-screen theme-green';
    if (btnBlue) btnBlue.classList.remove('active');
    if (btnGreen) btnGreen.classList.add('active');
    localStorage.setItem('traffic_lcd_theme', 'green');
  } else {
    glass.className = 'lcd-glass-screen theme-blue';
    if (btnBlue) btnBlue.classList.add('active');
    if (btnGreen) btnGreen.classList.remove('active');
    localStorage.setItem('traffic_lcd_theme', 'blue');
  }
}

// Khởi tạo các ô LCD và theme lưu trữ
initLcdCells();
const savedTheme = localStorage.getItem('traffic_lcd_theme') || 'blue';
setLcdTheme(savedTheme);

// ─── Bắt đầu vòng lặp polling ─────────────────────────────
poll();
setInterval(poll, 1000);



