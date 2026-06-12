import json

with open('workflows/WF_FLOW_MENU.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Create the node
cancel_node = {
  'parameters': {
    'operation': 'update',
    'documentId': { '__rl': True, 'value': '1ENztX5Jw-W8upEOijCgdVbi2_cHfBbOO0Y4O0s6rpuw', 'mode': 'id' },
    'sheetName': { '__rl': True, 'value': 'PEDIDOS', 'mode': 'name' },
    'columns': {
      'mappingMode': 'defineBelow',
      'value': { 'estado': 'CANCELADO' },
      'matchingColumns': [], 'schema': [], 'attemptToConvertTypes': False, 'convertFieldsToString': True
    },
    'options': { 'cellFormat': 'USER_ENTERED' },
    'filtersUI': {
      'values': [ { 'lookupColumn': 'id_pedido', 'lookupValue': '={{ $json.cancelOrderId }}' } ]
    }
  },
  'id': 'cancel-pedidos-node',
  'name': 'Cancel PEDIDOS',
  'type': 'n8n-nodes-base.googleSheets',
  'typeVersion': 4.5,
  'position': [300, 0],
  'credentials': { 'googleSheetsOAuth2Api': { 'id': '15AvKlr14Qt1VZsU', 'name': 'Google Sheets account' } }
}

jscode = """
const text = $('Execute Workflow Trigger').first().json.text || "";
let cancelOrderId = null;
if (text === "/cancelar") {
  try {
    let allPedidos = $('Read PEDIDOS').all().map(i => i.json);
    let myPending = allPedidos.filter(p => String(p.telegram_id) === String($('Execute Workflow Trigger').first().json.telegram_id) && p.estado === "RECIBIDO");
    if (myPending.length > 0) {
      cancelOrderId = myPending[myPending.length - 1].id_pedido;
    }
  } catch(e) {}
}
if (cancelOrderId) {
  return [{ json: { cancelOrderId: cancelOrderId, text: text } }];
}
return [{ json: { skip: true, text: text } }];
"""

# Create Check Cancel node
check_cancel_node = {
  'parameters': {
    'jsCode': jscode
  },
  'id': 'check-cancel-node',
  'name': 'Check Cancel',
  'type': 'n8n-nodes-base.code',
  'typeVersion': 2,
  'position': [300, -150]
}

# Create If node
if_cancel_node = {
  'parameters': {
    'conditions': {
      'string': [ { 'value1': '={{ $json.cancelOrderId }}', 'operation': 'isNotEmpty' } ]
    }
  },
  'id': 'if-cancel-node',
  'name': 'Has Cancel Order?',
  'type': 'n8n-nodes-base.if',
  'typeVersion': 1,
  'position': [450, -150]
}

# Add nodes
wf['nodes'].extend([check_cancel_node, if_cancel_node, cancel_node])

# Update connections
# Limit PEDIDOS -> Check Cancel
wf['connections']['Limit PEDIDOS'] = { 'main': [ [ { 'node': 'Check Cancel', 'type': 'main', 'index': 0 } ] ] }
# Check Cancel -> Has Cancel Order?
wf['connections']['Check Cancel'] = { 'main': [ [ { 'node': 'Has Cancel Order?', 'type': 'main', 'index': 0 } ] ] }
# Has Cancel Order? -> True: Cancel PEDIDOS, False: Format Main Menu
wf['connections']['Has Cancel Order?'] = { 'main': [
  [ { 'node': 'Cancel PEDIDOS', 'type': 'main', 'index': 0 } ],
  [ { 'node': 'Format Main Menu', 'type': 'main', 'index': 0 } ]
] }
# Cancel PEDIDOS -> Format Main Menu
wf['connections']['Cancel PEDIDOS'] = { 'main': [ [ { 'node': 'Format Main Menu', 'type': 'main', 'index': 0 } ] ] }

with open('workflows/WF_FLOW_MENU.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2)
print('Updated WF_FLOW_MENU.json')
