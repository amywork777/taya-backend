"""
Supabase database client - replaces Firebase/Firestore
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')

    if not url or not key:
        # For testing, use mock values
        url = url or "https://mock.supabase.co"
        key = key or "mock-key"
        print(f"⚠️ Using mock Supabase credentials: {url}")

    return create_client(url, key)

# Global client instance
supabase: Client = get_supabase_client()

# Helper functions to mimic Firestore API
class SupabaseFirestoreAdapter:
    """Adapter to make Supabase work like Firestore"""

    def __init__(self, client: Client):
        self.client = client

    def collection(self, name: str):
        return SupabaseCollection(self.client, name)

class SupabaseCollection:
    """Supabase collection that mimics Firestore collection"""

    def __init__(self, client: Client, table_name: str):
        self.client = client
        self.table_name = table_name

    def document(self, doc_id: str = None):
        return SupabaseDocument(self.client, self.table_name, doc_id)

    def add(self, data: Dict[str, Any]):
        """Add document (like Firestore add)"""
        # Add timestamp fields
        now = datetime.utcnow().isoformat()
        data_with_timestamps = {
            **data,
            'created_at': now,
            'updated_at': now,
        }

        result = self.client.table(self.table_name).insert(data_with_timestamps).execute()

        if result.data and len(result.data) > 0:
            return SupabaseDocumentReference(self.client, self.table_name, result.data[0]['id'])
        else:
            raise Exception(f"Failed to insert into {self.table_name}")

    def where(self, field: str, op: str, value: Any):
        """Filter documents (like Firestore where)"""
        return SupabaseQuery(self.client, self.table_name, [(field, op, value)])

    def order_by(self, field: str, direction: str = 'asc'):
        """Order documents"""
        return SupabaseQuery(self.client, self.table_name, [], order_field=field, order_direction=direction)

    def limit(self, count: int):
        """Limit results"""
        return SupabaseQuery(self.client, self.table_name, [], limit_count=count)

    def stream(self):
        """Get all documents"""
        result = self.client.table(self.table_name).select("*").execute()
        return [SupabaseDocumentSnapshot(doc) for doc in result.data or []]

class SupabaseDocument:
    """Supabase document that mimics Firestore document"""

    def __init__(self, client: Client, table_name: str, doc_id: str = None):
        self.client = client
        self.table_name = table_name
        self.doc_id = doc_id

    def set(self, data: Dict[str, Any]):
        """Set document data"""
        now = datetime.utcnow().isoformat()
        data_with_timestamps = {
            **data,
            'updated_at': now,
        }

        if self.doc_id:
            # Update existing
            data_with_timestamps['id'] = self.doc_id
            result = self.client.table(self.table_name).upsert(data_with_timestamps).execute()
        else:
            # Create new
            data_with_timestamps['created_at'] = now
            result = self.client.table(self.table_name).insert(data_with_timestamps).execute()

        return result

    def update(self, data: Dict[str, Any]):
        """Update document data"""
        if not self.doc_id:
            raise Exception("Cannot update document without ID")

        data['updated_at'] = datetime.utcnow().isoformat()
        result = self.client.table(self.table_name).update(data).eq('id', self.doc_id).execute()
        return result

    def delete(self):
        """Delete document"""
        if not self.doc_id:
            raise Exception("Cannot delete document without ID")

        result = self.client.table(self.table_name).delete().eq('id', self.doc_id).execute()
        return result

    def get(self):
        """Get document"""
        if not self.doc_id:
            return None

        result = self.client.table(self.table_name).select("*").eq('id', self.doc_id).execute()

        if result.data and len(result.data) > 0:
            return SupabaseDocumentSnapshot(result.data[0])
        return None

class SupabaseQuery:
    """Supabase query that mimics Firestore query"""

    def __init__(self, client: Client, table_name: str, filters: List = None,
                 order_field: str = None, order_direction: str = 'asc',
                 limit_count: int = None):
        self.client = client
        self.table_name = table_name
        self.filters = filters or []
        self.order_field = order_field
        self.order_direction = order_direction
        self.limit_count = limit_count

    def where(self, field: str, op: str, value: Any):
        """Add filter"""
        new_filters = self.filters + [(field, op, value)]
        return SupabaseQuery(
            self.client, self.table_name, new_filters,
            self.order_field, self.order_direction, self.limit_count
        )

    def order_by(self, field: str, direction: str = 'asc'):
        """Add ordering"""
        return SupabaseQuery(
            self.client, self.table_name, self.filters,
            field, direction, self.limit_count
        )

    def limit(self, count: int):
        """Add limit"""
        return SupabaseQuery(
            self.client, self.table_name, self.filters,
            self.order_field, self.order_direction, count
        )

    def stream(self):
        """Execute query and return results"""
        query = self.client.table(self.table_name).select("*")

        # Apply filters
        for field, op, value in self.filters:
            if op == '==':
                query = query.eq(field, value)
            elif op == '!=':
                query = query.neq(field, value)
            elif op == '>':
                query = query.gt(field, value)
            elif op == '>=':
                query = query.gte(field, value)
            elif op == '<':
                query = query.lt(field, value)
            elif op == '<=':
                query = query.lte(field, value)
            elif op == 'in':
                query = query.in_(field, value)

        # Apply ordering
        if self.order_field:
            ascending = self.order_direction == 'asc'
            query = query.order(self.order_field, desc=not ascending)

        # Apply limit
        if self.limit_count:
            query = query.limit(self.limit_count)

        result = query.execute()
        return [SupabaseDocumentSnapshot(doc) for doc in result.data or []]

class SupabaseDocumentSnapshot:
    """Supabase document snapshot that mimics Firestore document snapshot"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.id = data.get('id')

    def to_dict(self):
        """Get document data as dict"""
        return self._data

    def exists(self):
        """Check if document exists"""
        return self._data is not None

class SupabaseDocumentReference:
    """Supabase document reference"""

    def __init__(self, client: Client, table_name: str, doc_id: str):
        self.client = client
        self.table_name = table_name
        self.id = doc_id

# Create the global database instance that acts like Firestore
db = SupabaseFirestoreAdapter(supabase)