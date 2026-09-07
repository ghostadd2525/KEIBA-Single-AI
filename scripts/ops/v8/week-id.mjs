#!/usr/bin/env node
/**
 * Print current JST week id (YYYY-Www).
 */
import { jstParts, weekIdJst } from "./calendar.mjs";

const now = new Date();
const parts = jstParts(now);
console.log(
  JSON.stringify(
    {
      schema_version: "expect-v8-week-id/1.0",
      week_id: weekIdJst(now),
      date_jst: parts.date_jst,
      weekday: parts.weekday_name,
    },
    null,
    2
  )
);
