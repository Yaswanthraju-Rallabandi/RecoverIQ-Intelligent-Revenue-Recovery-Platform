const fs = require('fs');
const path = require('path');

const jsonPath = path.join(__dirname, 'synthetic_payments_50.json');
const csvPath = path.join(__dirname, 'synthetic_payments_50.csv');
const sqlPath = path.join(__dirname, 'schema.sql');

console.log('\n================================================================');
console.log('📊 DAY 1: ARCHITECTURE & SCHEMAS VERIFICATION');
console.log('================================================================\n');

if (fs.existsSync(sqlPath)) {
  console.log('✅ SQLite Schema created: data/schema.sql');
}

if (fs.existsSync(jsonPath) && fs.existsSync(csvPath)) {
  const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  console.log(`✅ Generated ${jsonData.length} Synthetic Failed Transactions (JSON & CSV)`);
  
  const methods = {};
  const failureCodes = {};
  let totalRiskAmount = 0;

  jsonData.forEach(p => {
    methods[p.method] = (methods[p.method] || 0) + 1;
    failureCodes[p.failure_code] = (failureCodes[p.failure_code] || 0) + 1;
    totalRiskAmount += Number(p.amount);
  });

  console.log('\n--- Summary of 50 Synthetic Records ---');
  console.log('Payment Methods Breakdown:', methods);
  console.log('Failure Codes Breakdown:', failureCodes);
  console.log(`Total Revenue at Risk: ₹${totalRiskAmount.toLocaleString('en-IN')}`);

  console.log('\nSample Record (PAY_1021):');
  console.log(jsonData[0]);
}

console.log('\n================================================================\n');