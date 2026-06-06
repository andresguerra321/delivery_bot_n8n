const fs = require('fs');

// Patch WF_MAIN_ROUTER.json
const routerFile = 'c:\\Users\\andre\\OneDrive\\Escritorio\\proyecto n8n\\workflows\\WF_MAIN_ROUTER.json';
const routerData = JSON.parse(fs.readFileSync(routerFile, 'utf8'));

routerData.nodes.forEach(n => {
  if (n.name === "Call 'WF_ADMIN_PANEL'") {
    if (n.parameters && n.parameters.workflowInputs && n.parameters.workflowInputs.value) {
      n.parameters.workflowInputs.value.callback_query_id = "={{ $('Extract Data').first().json.callback_query_id }}";
      n.parameters.workflowInputs.value.message_id = "={{ $('Extract Data').first().json.message_id }}";
    }
  }
});

fs.writeFileSync(routerFile, JSON.stringify(routerData, null, 2), 'utf8');

// Patch WF_ADMIN_PANEL.json
const adminFile = 'c:\\Users\\andre\\OneDrive\\Escritorio\\proyecto n8n\\workflows\\WF_ADMIN_PANEL.json';
let adminData = fs.readFileSync(adminFile, 'utf8');

// Replace reference in Answer Callback Query
adminData = adminData.replace(
  /\{\{ \$\('Telegram Trigger'\)\.first\(\)\.json\.callback_query\.id \}\}/g,
  "{{ $('admin-trigger').first().json.callback_query_id }}"
);

// Replace references in Parse Admin Action
adminData = adminData.replace(
  /const callbackData = \$\('Telegram Trigger'\)\.first\(\)\.json\.callback_query\.data;/g,
  "const callbackData = $('admin-trigger').first().json.callback_data;"
);

adminData = adminData.replace(
  /const chatId = \$\('Telegram Trigger'\)\.first\(\)\.json\.callback_query\.message\.chat\.id;/g,
  "const chatId = $('admin-trigger').first().json.chat_id;"
);

adminData = adminData.replace(
  /const messageId = \$\('Telegram Trigger'\)\.first\(\)\.json\.callback_query\.message\.message_id;/g,
  "const messageId = $('admin-trigger').first().json.message_id;"
);

fs.writeFileSync(adminFile, adminData, 'utf8');

console.log("Patched successfully!");
