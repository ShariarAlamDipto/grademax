import { auditToolBank } from './lib/tool_bank_audit'
auditToolBank('4EC1').catch(error => { console.error(error); process.exitCode = 1 })
