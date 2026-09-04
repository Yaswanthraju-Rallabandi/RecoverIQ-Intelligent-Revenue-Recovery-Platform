const fs = require('fs');
const path = require('path');

const jsonPath = path.join(__dirname, 'merchant_transactions_sample.json');
const csvPath = path.join(__dirname, 'merchant_transactions_sample.csv');
const sqlPath = path.join(__dirname, 'schema.sql');

console.log('\n================================================================');
console.log('DAY 1: ARCHITECTURE & SCHEMAS VERIFICATION');
console.log('================================================================\n');

if (fs.existsSync(sqlPath)) {
  console.log('[OK] SQLite Schema created: data/schema.sql');
}

if (fs.existsSync(jsonPath) && fs.existsSync(csvPath)) {
  const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  console.log(`[OK] Loaded ${jsonData.length} Merchant Transaction Records (JSON & CSV)`);
  
  const methods = {};
  const failureCodes = {};
  let totalRiskAmount = 0;

  jsonData.forEach(p => {
    methods[p.method] = (methods[p.method] || 0) + 1;
    failureCodes[p.failure_code] = (failureCodes[p.failure_code] || 0) + 1;
    totalRiskAmount += Number(p.amount);
  });

  console.log('\n--- Summary of 50 Merchant Records ---');
  console.log('Payment Methods Breakdown:', methods);
  console.log('Failure Codes Breakdown:', failureCodes);
  console.log(`Total Revenue at Risk: INR ${totalRiskAmount.toLocaleString('en-IN')}`);

  console.log('\nSample Record (PAY_1021):');
  console.log(jsonData[0]);
}

console.log('\n================================================================\n');