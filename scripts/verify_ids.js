const fs = require('fs');
const html = fs.readFileSync('outputs/html/hotel-management.html', 'utf-8');

// JS syntax check
try {
    new Function(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
    console.log('JS: OK');
} catch(e) {
    console.log('JS ERR:', e.message);
}

// Check all dynamic IDs
const ids = [
    'guest-struct-tbl', 'channel-source-tbl', 'review-stats-tbl',
    'staff-ratio-tbl', 'food-trend-tbl', 'pricing-compare-tbl',
    'co-kpi-cards', 'fnbBox', 'as-device-tbl', 'budget-tbl', 'cost-struct-tbl'
];
ids.forEach(id => {
    const found = html.includes('id="' + id + '"') || html.includes('id=' + id);
    console.log((found ? 'EXIST' : 'MISS') + ': ' + id);
});

// Count functions
const fns = html.match(/function\s+(\w+)/g) || [];
console.log('Functions:', fns.length);
