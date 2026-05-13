#!/usr/bin/env node
/**
 * One-time announcement email to all Supabase Auth users.
 *
 * Setup:
 *   1. Enable 2-Step Verification on grademax.me@gmail.com
 *   2. Create an App Password: https://myaccount.google.com/apppasswords
 *   3. Add to .env.local:
 *        GMAIL_USER=grademax.me@gmail.com
 *        GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
 *   4. Install nodemailer:  npm i nodemailer
 *
 * Usage:
 *   node scripts/send_announcement.mjs --dry-run          # list recipients, send nothing
 *   node scripts/send_announcement.mjs --test you@x.com   # send only to one address
 *   node scripts/send_announcement.mjs                    # send to everyone
 *   node scripts/send_announcement.mjs --resume           # skip addresses already in log
 *
 * State is written to scripts/email_send_log.json so re-runs can resume.
 */

import { createClient } from '@supabase/supabase-js'
import nodemailer from 'nodemailer'
import dotenv from 'dotenv'
import path from 'node:path'
import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: path.resolve(__dirname, '..', '.env.local') })

const SITE_URL = 'https://grademax.com'
const FROM_NAME = 'Grademax'
const SUBJECT = 'Grademax is back!'

const HTML_BODY = `
<!-- TODO: REPLACE WITH YOUR FINAL COPY -->
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;color:#111;line-height:1.6">
  <h2 style="color:#1a1a1a;margin-bottom:12px">Grademax is back!</h2>
  <p>Hi there,</p>
  <p>Just a quick note to let you know <strong>Grademax is back online</strong>.
     Your account, past papers, topics, and saved tests are all where you left them.</p>
  <p>
    <a href="${SITE_URL}"
       style="display:inline-block;background:#111;color:#fff;padding:10px 18px;
              border-radius:6px;text-decoration:none">Open Grademax</a>
  </p>
  <p style="color:#666;font-size:13px;margin-top:32px">
    You're receiving this because you registered an account at grademax.com.
    Reply to this email if you'd like to be removed from future updates.
  </p>
</div>
`.trim()

const TEXT_BODY = `
Grademax is back!

Hi there,

Just a quick note to let you know Grademax is back online.
Your account, past papers, topics, and saved tests are all where you left them.

Open Grademax: ${SITE_URL}

You're receiving this because you registered an account at grademax.com.
Reply to this email if you'd like to be removed from future updates.
`.trim()

const args = parseArgs(process.argv.slice(2))
const LOG_PATH = path.resolve(__dirname, 'email_send_log.json')
const THROTTLE_MS = 2000

function parseArgs(argv) {
  const out = { dryRun: false, test: null, resume: false, limit: null }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--dry-run') out.dryRun = true
    else if (a === '--resume') out.resume = true
    else if (a === '--test') out.test = argv[++i]
    else if (a === '--limit') out.limit = Number(argv[++i])
  }
  return out
}

function requireEnv(name) {
  const v = process.env[name]
  if (!v) throw new Error(`Missing required env var: ${name}`)
  return v
}

async function loadLog() {
  try {
    const raw = await fs.readFile(LOG_PATH, 'utf8')
    return JSON.parse(raw)
  } catch {
    return { sent: [], failed: [], startedAt: null, finishedAt: null }
  }
}

async function saveLog(log) {
  await fs.writeFile(LOG_PATH, JSON.stringify(log, null, 2))
}

async function fetchAllUsers(supabase) {
  const all = []
  let page = 1
  const perPage = 1000
  while (true) {
    const { data, error } = await supabase.auth.admin.listUsers({ page, perPage })
    if (error) throw error
    const users = data?.users ?? []
    all.push(...users)
    if (users.length < perPage) break
    page++
  }
  return all
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms))
}

async function main() {
  const SUPABASE_URL = requireEnv('NEXT_PUBLIC_SUPABASE_URL')
  const SERVICE_KEY = requireEnv('SUPABASE_SERVICE_ROLE_KEY')

  const supabase = createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: { persistSession: false }
  })

  console.log('Fetching users from Supabase Auth...')
  const users = await fetchAllUsers(supabase)
  const withEmail = users.filter(u => u.email && !u.banned_until)
  console.log(`Found ${users.length} total users, ${withEmail.length} with email.`)

  let recipients
  if (args.test) {
    recipients = [{ id: 'test', email: args.test }]
    console.log(`TEST MODE — sending only to ${args.test}`)
  } else {
    recipients = withEmail
  }

  const log = await loadLog()
  if (args.resume) {
    const alreadySent = new Set(log.sent.map(r => r.email.toLowerCase()))
    const before = recipients.length
    recipients = recipients.filter(r => !alreadySent.has(r.email.toLowerCase()))
    console.log(`RESUME — skipping ${before - recipients.length} already-sent addresses.`)
  }

  if (args.limit) {
    recipients = recipients.slice(0, args.limit)
    console.log(`LIMIT — capped to ${args.limit} recipients.`)
  }

  if (args.dryRun) {
    console.log('\n--- DRY RUN — recipients ---')
    recipients.forEach((r, i) => console.log(`${i + 1}. ${r.email}`))
    console.log(`\nWould send to ${recipients.length} addresses. No email sent.`)
    return
  }

  const GMAIL_USER = requireEnv('GMAIL_USER')
  const GMAIL_APP_PASSWORD = requireEnv('GMAIL_APP_PASSWORD')

  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: { user: GMAIL_USER, pass: GMAIL_APP_PASSWORD }
  })

  console.log('Verifying SMTP connection...')
  await transporter.verify()
  console.log('SMTP OK.\n')

  log.startedAt ??= new Date().toISOString()
  await saveLog(log)

  let ok = 0
  let fail = 0
  for (let i = 0; i < recipients.length; i++) {
    const r = recipients[i]
    const prefix = `[${i + 1}/${recipients.length}]`
    try {
      await transporter.sendMail({
        from: `"${FROM_NAME}" <${GMAIL_USER}>`,
        to: r.email,
        subject: SUBJECT,
        text: TEXT_BODY,
        html: HTML_BODY
      })
      log.sent.push({ email: r.email, at: new Date().toISOString() })
      ok++
      console.log(`${prefix} sent  -> ${r.email}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      log.failed.push({ email: r.email, at: new Date().toISOString(), error: msg })
      fail++
      console.error(`${prefix} FAIL  -> ${r.email}  (${msg})`)
    }

    if ((i + 1) % 10 === 0) await saveLog(log)
    if (i < recipients.length - 1) await sleep(THROTTLE_MS)
  }

  log.finishedAt = new Date().toISOString()
  await saveLog(log)

  console.log(`\nDone. Sent: ${ok}  Failed: ${fail}  Log: ${LOG_PATH}`)
  if (fail > 0) console.log('Re-run with --resume to retry only failed addresses.')
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
