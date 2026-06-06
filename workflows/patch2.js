const fs = require('fs');
const file = 'c:\\Users\\andre\\OneDrive\\Escritorio\\proyecto n8n\\workflows\\WF_ADMIN_PANEL.json';
let data = fs.readFileSync(file, 'utf8');

// The name of the trigger node is 'Execute Workflow Trigger', not 'admin-trigger'
data = data.replace(/\$\('admin-trigger'\)/g, "$('Execute Workflow Trigger')");

// Also Check Admin Callback node uses {{ $json.callback_query.data }}
// We must change it to {{ $json.callback_data }} because that's what the trigger passes now.
data = data.replace(/\{\{ \$json\.callback_query\.data \}\}/g, '={{ $json.callback_data }}');

fs.writeFileSync(file, data, 'utf8');
console.log('Fixed admin panel references successfully!');
