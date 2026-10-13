/**
 * TMX-14: Russian UX copy — matrix labels, T1–T3 tier names, tooltip strings.
 * Usage: import { RU } from "./i18n/ru.js"; then RU.surface, RU.tooltips.dominance, etc.
 */
export const RU = {
  // Surface / mode labels
  surface: "Поверхность",
  lattice288: "288 решётка",
  hex72k: "72к гексов",
  projection: "Проекция",

  projectionOptions: {
    flat: "Плоская (отладка)",
    diamond: "Ромб (по полосам)",
    cylinder: "Цилиндр (сектор-полоса)",
    spheroid: "Сфероид (3D)",
  },

  // Render modes
  renderModes: {
    dominant_area: "Доминантная область (по умолч.)",
    dominance_heat: "Тепловая карта доминирования",
    stability_heat: "Тепловая карта стабильности",
    delta: "Дельта (vs предыдущий кадр)",
    boundary: "Противоречие / граница",
    family_layout: "Инспекция семейного макета",
  },

  // Controls
  search: "Поиск",
  searchPlaceholder: "id, family_id, area_id, dominant_area…",
  topK: "Топ-K фильтр",
  speed: "Скорость (мс/кадр)",
  pinSelection: "Закрепить выбор по кадрам",
  coherence: "Когерентность",

  coherenceOptions: {
    area_scores: "Среднее area_scores соседей → re-argmax",
    dominance: "Сглаживание доминирования",
    stability: "Сглаживание стабильности",
  },

  // Tier labels (T1–T3)
  tiers: {
    T1: "T1 — Канонический",
    T2: "T2 — Производный",
    T3: "T3 — Исследовательский (не нормативный)",
  },

  // Hex info panel
  hexInfo: "Информация о гексе",
  noSelection: "Наведите или выберите гекс для инспекции.",
  areaScores: "area_scores[12]",
  dominance: "Доминирование",
  stability: "Стабильность",
  contradiction: "Противоречие",
  activation: "Активация",
  rawVsDisplay: "Сырое (тот же кадр, без когерентности)",
  vsPrevFrame: "vs предыдущий кадр",
  prevDominant: "предыдущая доминанта",
  areaSwitched: "смена области",

  // Relations panel
  relationsPanel: "Связи + Сигналы",
  relationsTab: "Дрейф",
  adTab: "Появление/Исчезновение",
  areaLabel: "область",
  driftVsImprint: "Дрейф области vs отпечаток сессии (L1 среднее)",
  appeared: "Появились",
  disappeared: "Исчезли",
  dominantShift: "Ведущий сдвиг",
  onsetFrame: "ф",  // frame abbreviation

  // Dominance mass card
  dominanceMassTitle: "Масса доминирования по области (отображение)",

  // Status badges
  zoomLabel: "масштаб",
  modeLabel: "режим",
  frameLabel: "кадр",
  coherenceLabel: "когерентность",
  hoverLabel: "наведение",
  selectedLabel: "выбрано",

  // Tooltips (hover annotations)
  tooltips: {
    dominance: "Доминирование: доля активации ведущей области над суммой.",
    stability: "Стабильность: инерция состояния между кадрами.",
    contradiction: "Противоречие: расстояние между двумя сильнейшими областями.",
    activation: "Активация: общая интенсивность отклика семейства.",
    drift: "Дрейф: отклонение от отпечатка сессии. >±0,15 — значимый сдвиг.",
    appeared: "Появившийся сигнал: семейство или область активировались впервые.",
    disappeared: "Исчезнувший сигнал: семейство или область утратили доминирование.",
    themeMarker: "Маркер темы: интерпретационная метка, не нормативная (T3).",
  },
};
