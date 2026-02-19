"""
Entity Extraction Module
Extracts named entities, relationships, and key concepts from text
"""

import re
from typing import List, Dict, Set


class EntityExtractor:
    """Extract entities and relationships from text"""
    
    def __init__(self):
        # Common entity patterns (simple regex-based for baseline)
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'url': r'https?://[^\s]+',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'money': r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
        }
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract entities from text"""
        entities = []
        entity_id = 0
        
        # Extract pattern-based entities
        for entity_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entities.append({
                    "id": f"entity_{entity_id}",
                    "type": entity_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
                entity_id += 1
        
        # Extract capitalized words as potential named entities
        capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.finditer(capitalized_pattern, text)
        
        seen_values = set()
        for match in matches:
            value = match.group()
            # Skip common words and duplicates
            if len(value) > 2 and value not in seen_values:
                seen_values.add(value)
                entities.append({
                    "id": f"entity_{entity_id}",
                    "type": "named_entity",
                    "value": value,
                    "start": match.start(),
                    "end": match.end()
                })
                entity_id += 1
        
        # Extract key phrases (simple noun phrases)
        key_phrases = self._extract_key_phrases(text)
        for phrase in key_phrases:
            entities.append({
                "id": f"entity_{entity_id}",
                "type": "key_phrase",
                "value": phrase,
                "start": -1,
                "end": -1
            })
            entity_id += 1
        
        return entities
    
    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from text"""
        # Simple frequency-based extraction
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in self._get_stop_words():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top phrases
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_phrases]]
    
    def _get_stop_words(self) -> Set[str]:
        """Common stop words to filter out"""
        return {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are',
            'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'them', 'their', 'what', 'which', 'who', 'when',
            'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'from', 'with', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
            'up', 'down', 'in', 'out', 'off', 'over', 'under', 'again', 'further',
            'then', 'once'
        }
    
    def extract_relationships(self, entities: List[Dict], text: str) -> List[Dict]:
        """Extract relationships between entities"""
        relationships = []
        
        # Simple co-occurrence based relationships
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # If entities appear close to each other, create a relationship
                if abs(entity1.get('start', 0) - entity2.get('start', 0)) < 100:
                    relationships.append({
                        "source": entity1["id"],
                        "target": entity2["id"],
                        "type": "co_occurs",
                        "weight": 1
                    })
        
        return relationships
