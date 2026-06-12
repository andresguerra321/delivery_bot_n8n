import json

with open('workflows/WF_ADMIN_PANEL.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Because the previous script may have inserted bad nodes, let's clean them up first
wf['nodes'] = [n for n in wf['nodes'] if n['id'] not in ['already-cancelled-node', 'update-msg-cancelled']]
# Also clean up connections if necessary
if 'Read Order - Prep' in wf['connections']:
    wf['connections']['Read Order - Prep'] = { 'main': [ [ { 'node': 'Update PEDIDOS - Prep', 'type': 'main', 'index': 0 } ] ] }
if 'Already Cancelled?' in wf['connections']:
    del wf['connections']['Already Cancelled?']

already_cancelled_node = {
  'parameters': {
    'conditions': {
      'options': {
        'caseSensitive': True,
        'leftValue': '',
        'typeValidation': 'strict'
      },
      'conditions': [
        {
          'id': 'c1',
          'leftValue': '={{ $(\'Read Order - Prep\').first().json.estado }}',
          'rightValue': 'CANCELADO',
          'operator': {
            'type': 'string',
            'operation': 'equals'
          }
        }
      ],
      'combinator': 'and'
    }
  },
  'id': 'already-cancelled-node',
  'name': 'Already Cancelled?',
  'type': 'n8n-nodes-base.if',
  'typeVersion': 2,
  'position': [1210, -100]
}

update_msg_cancelled = {
  'parameters': {
    'resource': 'message',
    'operation': 'editMessageText',
    'chatId': '={{ $(\'Parse Admin Action\').first().json.chatId }}',
    'messageId': '={{ $(\'Parse Admin Action\').first().json.messageId }}',
    'text': '=🚫 Pedido #{{ $(\'Parse Admin Action\').first().json.orderId }} — Estado: *CANCELADO POR EL USUARIO*',
    'replyMarkup': 'none',
    'additionalFields': {
      'parse_mode': 'Markdown'
    }
  },
  'id': 'update-msg-cancelled',
  'name': 'Update Kitchen Msg - Cancelled',
  'type': 'n8n-nodes-base.telegram',
  'typeVersion': 1.2,
  'position': [1420, -300],
  'credentials': {
    'telegramApi': {
      'id': 'ZK5tkFfqOriXG3BO',
      'name': 'Telegram account'
    }
  }
}

wf['nodes'].extend([already_cancelled_node, update_msg_cancelled])

# Re-route Read Order - Prep -> Already Cancelled? -> (True: Update Kitchen Msg - Cancelled, False: Update PEDIDOS - Prep)
wf['connections']['Read Order - Prep'] = { 'main': [ [ { 'node': 'Already Cancelled?', 'type': 'main', 'index': 0 } ] ] }
wf['connections']['Already Cancelled?'] = { 'main': [
  [ { 'node': 'Update Kitchen Msg - Cancelled', 'type': 'main', 'index': 0 } ],
  [ { 'node': 'Update PEDIDOS - Prep', 'type': 'main', 'index': 0 } ]
] }

# Since we are here, let's fix the Enroute bug. 
# The issue with Enroute bug is that Update Kitchen Msg - Enroute has `additionalFields: { callback_data: ... }` inside the inlineKeyboard layout in WF_ADMIN_PANEL.json instead of `callbackData`. Wait! n8n node properties inside inlineKeyboard `buttons` might need `callbackData`, NOT `additionalFields: { callback_data: ... }` in some versions, but actually in `Update Kitchen Msg - Prep` it uses `additionalFields: { callback_data }` and works!
# Let me verify what Update Kitchen Msg - Prep uses.
for n in wf['nodes']:
    if n['name'] == 'Update Kitchen Msg - Prep':
        # Let's see how the buttons are defined.
        print("Prep buttons:", n['parameters'].get('inlineKeyboard'))
        pass

with open('workflows/WF_ADMIN_PANEL.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2)
print('Fixed and updated WF_ADMIN_PANEL.json')
