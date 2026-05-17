(function () {
  const TYPE_META = {
    battle: { label: "Battle", color: "#d2a64c" },
    covert_ops: { label: "Ops", color: "#9ec65d" },
    caravan: { label: "Caravan", color: "#c75a43" },
  };

  function parseData() {
    const source = document.getElementById("attack-type-data");
    if (!source) {
      return [];
    }
    try {
      return JSON.parse(source.textContent || "[]");
    } catch {
      return [];
    }
  }

  function createSvgElement(name, attrs = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attrs)) {
      element.setAttribute(key, String(value));
    }
    return element;
  }

  function pointPath(points) {
    return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ");
  }

  function shortDate(value) {
    const parts = String(value).split("-");
    if (parts.length === 3) {
      return `${parts[1]}/${parts[2]}`;
    }
    return value;
  }

  function renderChart(container, rows) {
    container.replaceChildren();
    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "muted chart-empty";
      empty.textContent = "No attack data matches these filters.";
      container.appendChild(empty);
      return;
    }

    const days = [...new Set(rows.map((row) => row.day))].sort();
    const types = [...new Set(rows.map((row) => row.attack_type))].sort((a, b) => {
      const order = ["battle", "covert_ops", "caravan"];
      return (order.indexOf(a) === -1 ? 99 : order.indexOf(a)) - (order.indexOf(b) === -1 ? 99 : order.indexOf(b));
    });
    const counts = new Map(rows.map((row) => [`${row.day}:${row.attack_type}`, Number(row.attack_count) || 0]));
    const maxValue = Math.max(1, ...rows.map((row) => Number(row.attack_count) || 0));

    const width = 940;
    const height = 330;
    const margin = { top: 24, right: 26, bottom: 54, left: 46 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const xForDay = (day) => margin.left + (days.length === 1 ? plotWidth / 2 : (days.indexOf(day) / (days.length - 1)) * plotWidth);
    const yForValue = (value) => margin.top + plotHeight - (value / maxValue) * plotHeight;

    const svg = createSvgElement("svg", {
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": "Attack types over time",
    });

    for (let i = 0; i <= 4; i += 1) {
      const value = Math.round((maxValue / 4) * i);
      const y = yForValue(value);
      svg.appendChild(createSvgElement("line", {
        class: "chart-grid-line",
        x1: margin.left,
        x2: width - margin.right,
        y1: y,
        y2: y,
      }));
      const label = createSvgElement("text", {
        class: "chart-axis-label",
        x: margin.left - 10,
        y: y + 4,
        "text-anchor": "end",
      });
      label.textContent = value;
      svg.appendChild(label);
    }

    const tickEvery = Math.max(1, Math.ceil(days.length / 7));
    days.forEach((day, index) => {
      if (index % tickEvery !== 0 && index !== days.length - 1) {
        return;
      }
      const x = xForDay(day);
      svg.appendChild(createSvgElement("line", {
        class: "chart-tick",
        x1: x,
        x2: x,
        y1: margin.top + plotHeight,
        y2: margin.top + plotHeight + 6,
      }));
      const label = createSvgElement("text", {
        class: "chart-axis-label",
        x,
        y: height - 25,
        "text-anchor": "middle",
      });
      label.textContent = shortDate(day);
      svg.appendChild(label);
    });

    types.forEach((type) => {
      const meta = TYPE_META[type] || { label: type, color: "#eee8d6" };
      const points = days.map((day) => ({
        x: xForDay(day),
        y: yForValue(counts.get(`${day}:${type}`) || 0),
      }));
      svg.appendChild(createSvgElement("path", {
        class: "chart-line",
        d: pointPath(points),
        fill: "none",
        stroke: meta.color,
      }));
      points.forEach((point, index) => {
        const value = counts.get(`${days[index]}:${type}`) || 0;
        if (value === 0) {
          return;
        }
        const dot = createSvgElement("circle", {
          class: "chart-dot",
          cx: point.x,
          cy: point.y,
          r: 4,
          fill: meta.color,
        });
        dot.appendChild(createSvgElement("title"));
        dot.querySelector("title").textContent = `${meta.label}: ${value} on ${days[index]}`;
        svg.appendChild(dot);
      });
    });

    const legend = document.createElement("div");
    legend.className = "chart-legend";
    types.forEach((type) => {
      const meta = TYPE_META[type] || { label: type, color: "#eee8d6" };
      const item = document.createElement("span");
      item.innerHTML = `<i style="background:${meta.color}"></i>${meta.label}`;
      legend.appendChild(item);
    });

    container.appendChild(svg);
    container.appendChild(legend);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("attack-type-chart");
    if (!container) {
      return;
    }
    renderChart(container, parseData());
  });
})();
