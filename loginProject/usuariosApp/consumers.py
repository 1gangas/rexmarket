import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async  
from .models import Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        if self.scope['user'].is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'En línea',
                    'user_id': self.scope['user'].id,
                    'is_new': True
                }
            )

    async def disconnect(self, close_code):
        if self.scope['user'].is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'Desconectado',
                    'user_id': self.scope['user'].id,
                    'is_new': False
                }
            )
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')
        
        # --- NUEVA LÓGICA DE PING-PONG ---
        if action == 'reply_status':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'En línea',
                    'user_id': self.scope['user'].id,
                    'is_new': False
                }
            )
            return
        elif action == 'ping':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'status': 'ping',
                    'user_id': self.scope['user'].id,
                    'is_new': False
                }
            )
            return

        message = text_data_json.get('message')
        if message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                }
            )

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'status': event['status'],
            'user_id': event['user_id'],
            'is_new': event.get('is_new', False)
        }))

    # --- NUEVO: Enviar la confirmación de lectura al frontend ---
    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'user_id': event['user_id']
        }))

    # --- NUEVO: Función segura para actualizar la base de datos de forma asíncrona ---
    @database_sync_to_async
    def update_unread_messages(self):
        Message.objects.filter(
            conversation_id=self.conversation_id
        ).exclude(
            sender_id=self.scope['user'].id
        ).filter(is_read=False).update(is_read=True)