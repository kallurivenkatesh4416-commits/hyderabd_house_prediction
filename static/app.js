const form = document.querySelector("#predictionForm");
const controls = {
  location: document.querySelector("#location"),
  building_status: document.querySelector("#building_status"),
  property_type: document.querySelector("#property_type"),
  bhk: document.querySelector("#bhk"),
  area_insqft: document.querySelector("#area_insqft"),
};

const elements = {
  datasetLine: document.querySelector("#datasetLine"),
  priceResult: document.querySelector("#priceResult"),
  priceSubline: document.querySelector("#priceSubline"),
  areaMetric: document.querySelector("#areaMetric"),
  bhkMetric: document.querySelector("#bhkMetric"),
  statusMetric: document.querySelector("#statusMetric"),
  typeMetric: document.querySelector("#typeMetric"),
  medianPrice: document.querySelector("#medianPrice"),
  medianArea: document.querySelector("#medianArea"),
  popularLocations: document.querySelector("#popularLocations"),
};

let options = null;

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  });
}

function formatLakh(value) {
  const lakh = Number(value || 0);
  if (lakh >= 100) {
    return `₹ ${(lakh / 100).toFixed(2)} Cr`;
  }
  return `₹ ${lakh.toFixed(2)} L`;
}

function fillSelect(select, values, selectedValue) {
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (String(value) === String(selectedValue)) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function syncPlotBhk() {
  if (controls.property_type.value === "Residential Plot") {
    controls.bhk.value = "0";
  } else if (controls.bhk.value === "0") {
    controls.bhk.value = "3";
  }
}

function renderDatasetStats() {
  const rows = formatNumber(options.dataset.rows);
  const locations = formatNumber(options.dataset.locations);
  elements.datasetLine.textContent = `${rows} records · ${locations} locations`;
  elements.medianPrice.textContent = formatLakh(options.dataset.median_price_lakh);
  elements.medianArea.textContent = `${formatNumber(options.dataset.median_area)} sqft`;
}

function renderPopularLocations() {
  elements.popularLocations.innerHTML = "";
  options.popular_locations.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "location-pill";
    button.innerHTML = `<span>${item.name}</span><strong>${formatNumber(item.count)}</strong>`;
    button.addEventListener("click", () => {
      controls.location.value = item.name;
      predict();
    });
    elements.popularLocations.appendChild(button);
  });
}

function collectPayload() {
  return {
    location: controls.location.value,
    building_status: controls.building_status.value,
    property_type: controls.property_type.value,
    bhk: Number(controls.bhk.value),
    area_insqft: Number(controls.area_insqft.value),
  };
}

function setLoading(isLoading) {
  form.classList.toggle("is-loading", isLoading);
}

async function predict() {
  setLoading(true);
  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Prediction failed");

    elements.priceResult.textContent = result.prediction_label;
    elements.priceSubline.textContent = `${controls.property_type.value} in ${controls.location.value}`;
    elements.areaMetric.textContent = `${formatNumber(result.input.area_insqft)} sqft`;
    elements.bhkMetric.textContent = formatNumber(result.input.bhk);
    elements.statusMetric.textContent = result.input.building_status;
    elements.typeMetric.textContent = result.input.property_type;
  } catch (error) {
    elements.priceResult.textContent = "Unable to predict";
    elements.priceSubline.textContent = error.message;
  } finally {
    setLoading(false);
  }
}

async function init() {
  const response = await fetch("/api/options");
  options = await response.json();

  fillSelect(controls.location, options.locations, options.defaults.location);
  fillSelect(controls.building_status, options.building_statuses, options.defaults.building_status);
  fillSelect(controls.property_type, options.property_types, options.defaults.property_type);
  fillSelect(controls.bhk, options.bhk_values, options.defaults.bhk);

  controls.area_insqft.value = options.defaults.area_insqft;

  renderDatasetStats();
  renderPopularLocations();
  predict();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  syncPlotBhk();
  predict();
});

Object.values(controls).forEach((control) => {
  control.addEventListener("change", () => {
    if (!options) return;
    if (control === controls.property_type) {
      syncPlotBhk();
    }
    predict();
  });
});

init();
