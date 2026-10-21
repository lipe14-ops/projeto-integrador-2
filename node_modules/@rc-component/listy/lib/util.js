"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.toTaggedKey = void 0;
/** Which kind of entity a tagged key addresses. */

/**
 * Build the type-tagged key (`item:x` / `group:x`) used for virtual row keys,
 * scroll targets, getSize lookups and raw-mode data-key attributes, so item
 * and group keys can never collide. Constructed and compared as a whole —
 * never parsed back.
 */
const toTaggedKey = (oriKey, type) => `${type}:${oriKey}`;
exports.toTaggedKey = toTaggedKey;