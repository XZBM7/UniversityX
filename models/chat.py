from config import db
from bson.objectid import ObjectId
from datetime import datetime

chats = db.chats

def send_message(sender_id, receiver_id, message):
    chat_message = {
        'sender_id': ObjectId(sender_id),
        'receiver_id': ObjectId(receiver_id),
        'message': message,
        'timestamp': datetime.utcnow()
    }
    result = chats.insert_one(chat_message)
    return str(result.inserted_id)

def get_conversation(user1_id, user2_id):
    return list(chats.find({
        '$or': [
            {'sender_id': ObjectId(user1_id), 'receiver_id': ObjectId(user2_id)},
            {'sender_id': ObjectId(user2_id), 'receiver_id': ObjectId(user1_id)},
        ]
    }).sort('timestamp', 1))

def delete_chat_message(id):
    return chats.delete_one({'_id': ObjectId(id)})
