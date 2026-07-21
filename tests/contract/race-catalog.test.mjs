import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mapPiCatalogToWebItems, mapPiRaceToWebItem } from "../../functions/_lib/raceCatalog.js";

const sampleRace = {
  race_id: "2026-07-25-01-06",
  race_date: "2026-07-25",
  date: "2026-07-25",
  course: "新潟",
  venue: "新潟",
  race_number: 6,
  race_no: 6,
  race_label: "新潟6R",
  race_name: "豊栄特別",
  status: "published",
};

describe("race catalog mapping (PI → Web)", () => {
  it("mapPiRaceToWebItem: PI フィールドと互換 race_info", () => {
    const item = mapPiRaceToWebItem(sampleRace);
    assert.equal(item.race_id, "2026-07-25-01-06");
    assert.equal(item.race_label, "新潟6R");
    assert.equal(item.race_name, "豊栄特別");
    assert.equal(item.course, "新潟");
    assert.equal(item.race_number, 6);
    assert.equal(item.status, "published");
    assert.equal(item.race_info.venue, "新潟");
    assert.equal(item.race_info.race_no, 6);
    assert.equal(item.race_info.class_label, "豊栄特別");
    assert.equal(item.race_info.race_label, "新潟6R");
  });

  it("mapPiCatalogToWebItems: races 配列を変換", () => {
    const items = mapPiCatalogToWebItems({
      date: "2026-07-25",
      count: 1,
      races: [sampleRace],
    });
    assert.equal(items.length, 1);
    assert.equal(items[0].race_name, "豊栄特別");
  });
});
