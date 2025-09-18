import copy
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
import os

from ._client import db
from database.supabase_client import supabase
from database import users as users_db
from utils import encryption
from .helpers import set_data_protection_level, prepare_for_write, prepare_for_read

memories_collection = 'memories'
users_collection = 'users'


# *********************************
# ******* ENCRYPTION HELPERS ******
# *********************************


def _encrypt_memory_data(memory_data: Dict[str, Any], uid: str) -> Dict[str, Any]:
    data = copy.deepcopy(memory_data)

    if 'content' in data and isinstance(data['content'], str):
        data['content'] = encryption.encrypt(data['content'], uid)
    return data


def _decrypt_memory_data(memory_data: Dict[str, Any], uid: str) -> Dict[str, Any]:
    data = copy.deepcopy(memory_data)

    if 'content' in data and isinstance(data['content'], str):
        try:
            data['content'] = encryption.decrypt(data['content'], uid)
        except Exception:
            pass
    return data


def _prepare_data_for_write(data: Dict[str, Any], uid: str, level: str) -> Dict[str, Any]:
    if level == 'enhanced':
        return _encrypt_memory_data(data, uid)
    return data


def _prepare_memory_for_read(memory_data: Optional[Dict[str, Any]], uid: str) -> Optional[Dict[str, Any]]:
    if not memory_data:
        return None

    level = memory_data.get('data_protection_level')
    if level == 'enhanced':
        return _decrypt_memory_data(memory_data, uid)

    return memory_data


# *****************************
# ********** CRUD *************
# *****************************


@prepare_for_read(decrypt_func=_prepare_memory_for_read)
def get_memories(uid: str, limit: int = 100, offset: int = 0, categories: List[str] = []):
    print('get_memories db', uid, limit, offset, categories)
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        try:
            q = supabase.table('memories').select('*').eq('uid', uid)
            if categories:
                q = q.in_('category', categories)
            # Order by scoring desc then created_at desc
            try:
                q = q.order('scoring', desc=True).order('created_at', desc=True)
            except Exception:
                q = q.order('created_at', desc=True)
            try:
                q = q.range(offset, max(0, offset + limit - 1))
            except Exception:
                pass
            res = q.execute()
            memories = res.data or []
            print("get_memories", len(memories))
            result = [m for m in memories if m.get('user_review') is not False]
            return result
        except Exception as e:
            print('supabase get_memories error', e)
            return []

    memories_ref = db.collection(users_collection).document(uid).collection(memories_collection)
    if categories:
        memories_ref = memories_ref.where(filter=FieldFilter('category', 'in', categories))

    memories_ref = (
        memories_ref.order_by('scoring', direction=firestore.Query.DESCENDING)
        .order_by('created_at', direction=firestore.Query.DESCENDING)
        .limit(limit)
        .offset(offset)
    )

    # TODO: put user review to firestore query
    memories = [doc.to_dict() for doc in memories_ref.stream()]
    print("get_memories", len(memories))
    result = [memory for memory in memories if memory['user_review'] is not False]
    return result


@prepare_for_read(decrypt_func=_prepare_memory_for_read)
def get_user_public_memories(uid: str, limit: int = 100, offset: int = 0):
    print('get_public_memories', limit, offset)
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        try:
            q = (
                supabase.table('memories')
                .select('*')
                .eq('uid', uid)
                .eq('visibility', 'public')
                .order('scoring', desc=True)
                .order('created_at', desc=True)
            )
            try:
                q = q.range(offset, max(0, offset + limit - 1))
            except Exception:
                pass
            res = q.execute()
            return res.data or []
        except Exception as e:
            print('supabase get_user_public_memories error', e)
            return []

    memories_ref = db.collection(users_collection).document(uid).collection(memories_collection)
    memories_ref = memories_ref.order_by('scoring', direction=firestore.Query.DESCENDING).order_by(
        'created_at', direction=firestore.Query.DESCENDING
    )

    memories_ref = memories_ref.limit(limit).offset(offset)

    memories = [doc.to_dict() for doc in memories_ref.stream()]

    # Consider visibility as 'public' if it's missing
    public_memories = [memory for memory in memories if memory.get('visibility', 'public') == 'public']

    return public_memories


@prepare_for_read(decrypt_func=_prepare_memory_for_read)
def get_non_filtered_memories(uid: str, limit: int = 100, offset: int = 0):
    print('get_non_filtered_memories', uid, limit, offset)
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        try:
            q = (
                supabase.table('memories')
                .select('*')
                .eq('uid', uid)
                .order('created_at', desc=True)
            )
            try:
                q = q.range(offset, max(0, offset + limit - 1))
            except Exception:
                pass
            res = q.execute()
            return res.data or []
        except Exception as e:
            print('supabase get_non_filtered_memories error', e)
            return []

    memories_ref = db.collection(users_collection).document(uid).collection(memories_collection)
    memories_ref = memories_ref.order_by('created_at', direction=firestore.Query.DESCENDING)
    memories_ref = memories_ref.limit(limit).offset(offset)
    memories = [doc.to_dict() for doc in memories_ref.stream()]
    return memories


@set_data_protection_level(data_arg_name='data')
@prepare_for_write(data_arg_name='data', prepare_func=_prepare_data_for_write)
def create_memory(uid: str, data: dict):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        payload = data.copy()
        payload['uid'] = uid
        if 'created_at' in payload and isinstance(payload['created_at'], datetime):
            payload['created_at'] = payload['created_at'].isoformat()
        if 'updated_at' in payload and isinstance(payload['updated_at'], datetime):
            payload['updated_at'] = payload['updated_at'].isoformat()
        supabase.table('memories').upsert(payload).execute()
        return
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    memory_ref = memories_ref.document(data['id'])
    memory_ref.set(data)


@set_data_protection_level(data_arg_name='data')
@prepare_for_write(data_arg_name='data', prepare_func=_prepare_data_for_write)
def save_memories(uid: str, data: List[dict]):
    if not data:
        return
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        rows = []
        for memory in data:
            payload = memory.copy()
            payload['uid'] = uid
            if 'created_at' in payload and isinstance(payload['created_at'], datetime):
                payload['created_at'] = payload['created_at'].isoformat()
            if 'updated_at' in payload and isinstance(payload['updated_at'], datetime):
                payload['updated_at'] = payload['updated_at'].isoformat()
            rows.append(payload)
        if rows:
            supabase.table('memories').upsert(rows).execute()
        return

    batch = db.batch()
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    for memory in data:
        memory_ref = memories_ref.document(memory['id'])
        batch.set(memory_ref, memory)
    batch.commit()


def delete_memories(uid: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        supabase.table('memories').delete().eq('uid', uid).execute()
        return
    batch = db.batch()
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    for doc in memories_ref.stream():
        batch.delete(doc.reference)
    batch.commit()


@prepare_for_read(decrypt_func=_prepare_memory_for_read)
def get_memory(uid: str, memory_id: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        res = (
            supabase.table('memories').select('*').eq('uid', uid).eq('id', memory_id).single().execute()
        )
        return res.data if res and getattr(res, 'data', None) else None
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    memory_ref = memories_ref.document(memory_id)
    memory_data = memory_ref.get().to_dict()
    return memory_data


def review_memory(uid: str, memory_id: str, value: bool):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        supabase.table('memories').update({'reviewed': True, 'user_review': value}).eq('uid', uid).eq('id', memory_id).execute()
        return
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    memory_ref = memories_ref.document(memory_id)
    memory_ref.update({'reviewed': True, 'user_review': value})


def change_memory_visibility(uid: str, memory_id: str, value: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        supabase.table('memories').update({'visibility': value}).eq('uid', uid).eq('id', memory_id).execute()
        return
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    memory_ref = memories_ref.document(memory_id)
    memory_ref.update({'visibility': value})


def edit_memory(uid: str, memory_id: str, value: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        # Fetch to determine encryption level
        res = supabase.table('memories').select('data_protection_level').eq('uid', uid).eq('id', memory_id).single().execute()
        if not res or not getattr(res, 'data', None):
            return
        doc_level = res.data.get('data_protection_level', 'standard')
        content = value
        if doc_level == 'enhanced':
            content = encryption.encrypt(content, uid)
        supabase.table('memories').update({'content': content, 'edited': True, 'updated_at': datetime.now(timezone.utc).isoformat()}).eq('uid', uid).eq('id', memory_id).execute()
        return
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    memory_ref = memories_ref.document(memory_id)

    doc_snapshot = memory_ref.get()
    if not doc_snapshot.exists:
        return

    doc_level = doc_snapshot.to_dict().get('data_protection_level', 'standard')
    content = value
    if doc_level == 'enhanced':
        content = encryption.encrypt(content, uid)

    memory_ref.update({'content': content, 'edited': True, 'updated_at': datetime.now(timezone.utc)})


def delete_memory(uid: str, memory_id: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        supabase.table('memories').delete().eq('uid', uid).eq('id', memory_id).execute()
        return
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    memory_ref = memories_ref.document(memory_id)
    memory_ref.delete()


def delete_all_memories(uid: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        supabase.table('memories').delete().eq('uid', uid).execute()
        return
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    batch = db.batch()
    for doc in memories_ref.stream():
        batch.delete(doc.reference)
    batch.commit()


def delete_memories_for_conversation(uid: str, memory_id: str):
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        res = supabase.table('memories').delete().eq('uid', uid).eq('memory_id', memory_id).execute()
        print('delete_memories_for_conversation', memory_id, len(res.data or []))
        return
    batch = db.batch()
    user_ref = db.collection(users_collection).document(uid)
    memories_ref = user_ref.collection(memories_collection)
    query = memories_ref.where(filter=FieldFilter('memory_id', '==', memory_id))

    removed_ids = []
    for doc in query.stream():
        batch.delete(doc.reference)
        removed_ids.append(doc.id)
    batch.commit()
    print('delete_memories_for_conversation', memory_id, len(removed_ids))


def unlock_all_memories(uid: str):
    """
    Finds all memories for a user with is_locked: True and updates them to is_locked = False.
    """
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        supabase.table('memories').update({'is_locked': False}).eq('uid', uid).eq('is_locked', True).execute()
        print(f"Unlocked all memories for user {uid}")
        return
    memories_ref = db.collection(users_collection).document(uid).collection(memories_collection)
    locked_memories_query = memories_ref.where(filter=FieldFilter('is_locked', '==', True))

    batch = db.batch()
    docs = locked_memories_query.stream()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {'is_locked': False})
        count += 1
        if count >= 499:  # Firestore batch limit is 500
            batch.commit()
            batch = db.batch()
            count = 0
    if count > 0:
        batch.commit()
    print(f"Unlocked all memories for user {uid}")


# **************************************
# ********* MIGRATION HELPERS **********
# **************************************


def get_memories_to_migrate(uid: str, target_level: str) -> List[dict]:
    """
    Finds all memories that are not at the target protection level by fetching all documents
    and filtering them in memory. This simplifies the code but may be less performant for
    users with a very large number of documents.
    """
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        res = supabase.table('memories').select('id,data_protection_level').eq('uid', uid).execute()
        to_migrate = []
        for row in (res.data or []):
            current_level = row.get('data_protection_level', 'standard')
            if target_level != current_level:
                to_migrate.append({'id': row.get('id'), 'type': 'memory'})
        return to_migrate

    memories_ref = db.collection(users_collection).document(uid).collection(memories_collection)
    all_memories = memories_ref.select(['data_protection_level']).stream()

    to_migrate = []
    for doc in all_memories:
        doc_data = doc.to_dict()
        current_level = doc_data.get('data_protection_level', 'standard')
        if target_level != current_level:
            to_migrate.append({'id': doc.id, 'type': 'memory'})

    return to_migrate


def migrate_memories_level_batch(uid: str, memory_ids: List[str], target_level: str):
    """
    Migrates a batch of memories to the target protection level.
    """
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        res = supabase.table('memories').select('id,content,data_protection_level').eq('uid', uid).in_('id', memory_ids).execute()
        rows = res.data or []
        for row in rows:
            current_level = row.get('data_protection_level', 'standard')
            if current_level == target_level:
                continue
            plain_content = row.get('content')
            migrated_content = plain_content
            if target_level == 'enhanced' and isinstance(plain_content, str):
                migrated_content = encryption.encrypt(plain_content, uid)
            supabase.table('memories').update({'data_protection_level': target_level, 'content': migrated_content}).eq('uid', uid).eq('id', row.get('id')).execute()
        return

    batch = db.batch()
    memories_ref = db.collection(users_collection).document(uid).collection(memories_collection)
    doc_refs = [memories_ref.document(mem_id) for mem_id in memory_ids]
    doc_snapshots = db.get_all(doc_refs)

    for doc_snapshot in doc_snapshots:
        if not doc_snapshot.exists:
            print(f"Memory {doc_snapshot.id} not found, skipping.")
            continue

        memory_data = doc_snapshot.to_dict()
        current_level = memory_data.get('data_protection_level', 'standard')

        if current_level == target_level:
            continue

        # Decrypt the data first (if needed) to get a clean slate.
        plain_data = _prepare_memory_for_read(memory_data, uid)

        plain_content = plain_data.get('content')
        migrated_content = plain_content
        if target_level == 'enhanced':
            if isinstance(plain_content, str):
                migrated_content = encryption.encrypt(plain_content, uid)

        # Update the document with the migrated data and the new protection level.
        update_data = {'data_protection_level': target_level, 'content': migrated_content}
        batch.update(doc_snapshot.reference, update_data)

    batch.commit()


def migrate_memories(prev_uid: str, new_uid: str, app_id: str = None):
    """
    Migrate memories from one user to another.
    If app_id is provided, only migrate memories related to that app.
    """
    print(f'Migrating memories from {prev_uid} to {new_uid}')

    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
        q = supabase.table('memories').select('*').eq('uid', prev_uid)
        if app_id:
            q = q.eq('app_id', app_id)
        res = q.execute()
        rows = res.data or []
        if not rows:
            print(f'No memories to migrate for user {prev_uid}')
            return 0
        # Upsert with new uid
        for row in rows:
            row['uid'] = new_uid
        supabase.table('memories').upsert(rows).execute()
        print(f'Migrated {len(rows)} memories from {prev_uid} to {new_uid}')
        return len(rows)

    # Get source memories
    prev_user_ref = db.collection(users_collection).document(prev_uid)
    prev_memories_ref = prev_user_ref.collection(memories_collection)

    # Apply app_id filter if provided
    if app_id:
        query = prev_memories_ref.where(filter=FieldFilter('app_id', '==', app_id))
    else:
        query = prev_memories_ref

    # Get memories to migrate
    memories_to_migrate = [doc.to_dict() for doc in query.stream()]

    if not memories_to_migrate:
        print(f'No memories to migrate for user {prev_uid}')
        return 0

    # Create batch for destination user
    batch = db.batch()
    new_user_ref = db.collection(users_collection).document(new_uid)
    new_memories_ref = new_user_ref.collection(memories_collection)

    # Add memories to batch
    for memory in memories_to_migrate:
        memory_ref = new_memories_ref.document(memory['id'])
        batch.set(memory_ref, memory)

    # Commit batch
    batch.commit()
    print(f'Migrated {len(memories_to_migrate)} memories from {prev_uid} to {new_uid}')
    return len(memories_to_migrate)
