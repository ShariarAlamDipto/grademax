import { test } from "node:test"
import assert from "node:assert/strict"
import { HEARTBEAT_SECONDS, isHeartbeatDue } from "../src/lib/visitBeacon"

test("a heartbeat is due after five minutes of unsent active time", () => {
  assert.equal(HEARTBEAT_SECONDS, 300)
  assert.equal(isHeartbeatDue(299, 0), false)
  assert.equal(isHeartbeatDue(300, 0), true)
  assert.equal(isHeartbeatDue(900, 700), false)
  assert.equal(isHeartbeatDue(1000, 700), true)
})

test("the session refresh outlives the gap between heartbeats", () => {
  // Session cookie: 30 minutes. A reader active on one page sends a heartbeat
  // at least every HEARTBEAT_SECONDS of active time, well inside that window.
  assert.ok(HEARTBEAT_SECONDS < 30 * 60)
})
