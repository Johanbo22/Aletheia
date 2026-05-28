"""
Help Manager module for managing help topics and tutorials

This module provides the HelpManager class which handles fetching help topics
and tutorial content from the SQLite database.
"""
import logging
import sqlite3
import textwrap
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

@dataclass(frozen=True)
class HelpTopicDetail:
    topic_id: str
    title: str
    description: str
    detailed_description: Optional[str]
    link: Optional[str]

logger = logging.getLogger(__name__)

class HelpManager:
    """Manages the connection and fetching of help /tutorials from the help database"""

    def __init__(self, db_name: str = "tutorial.db") -> None:
        self.base_dir: Path = Path(__file__).resolve().parent.parent
        self.db_path: Path = self.base_dir / "resources" / db_name

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Connection to the database"""
        if not self.db_path.exists():
            logger.error(f"Help database not found at: {self.db_path}")
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as error:
            logger.error(f"An error ocurred connecting to the database: {str(error)}")
            return None

    def get_help_topic(self, topic_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Fetches the topic from the database that the user requests.
        
        Args:
            topic_id (str): The unique id for the topic

        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]: (title, description, link)
        """
        conn = self._get_connection()
        if not conn:
            logger.debug("No database connection available")
            return None, None, None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, description, link FROM help_topics WHERE topic_Id = ?",
                (topic_id,)
            )
            row = cursor.fetchone()
            if row:
                title: str = row["title"]
                
                raw_desc: Optional[str] = row["description"]
                description: str = textwrap.dedent(raw_desc).strip() if raw_desc else ""
                
                link: Optional[str] = row["link"]
                if isinstance(link, str):
                    link = link.strip()
                else:
                    link = None
                
                return title, description, link
            else:
                logger.debug(f"No topic found with topic_id: {topic_id}")
                return None, None, None
        except sqlite3.Error as error:
            logger.error(f"Error fetching data for topic_id {topic_id}: {str(error)}")
            return None, None, None
        finally:
            conn.close()
    
    def get_all_help_topics(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Retrieves all available help topics from database
        """
        conn = self._get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT topic_id, title, COALESCE(type, 'Uncategorized') as category FROM help_topics ORDER BY category ASC, title ASC")
            rows = cursor.fetchall()
            grouped_topics: Dict[str, List[Dict[str, str]]] = {}
            for row in rows:
                category = row["category"]
                if category not in grouped_topics:
                    grouped_topics[category] = []
                    
                grouped_topics[category].append({
                    "topic_id": row["topic_id"], 
                    "title": row["title"]
                })
                
            return grouped_topics
        except sqlite3.Error as error:
            logger.error(f"Error fetching all help topics: {str(error)}")
            return {}
        finally:
            conn.close()
    
    def get_detailed_help_topic(self, topic_id: str) -> Optional[HelpTopicDetail]:
        """
        Fetches the detailed description of a topic id from the database
        """
        conn = self._get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, description, detailed_description, link FROM help_topics WHERE topic_id = ?",
                (topic_id,)
            )
            row = cursor.fetchone()
            
            if row:
                raw_desc: Optional[str] = row["description"]
                raw_detailed_desc: Optional[str] = row["detailed_description"]
                
                return HelpTopicDetail(
                    topic_id=topic_id,
                    title=row["title"],
                    description=textwrap.dedent(raw_desc).strip() if raw_desc else "",
                    detailed_description=textwrap.dedent(raw_detailed_desc).strip() if raw_detailed_desc else None,
                    link=row["link"].strip() if isinstance(row["link"], str) else None
                )
            return None
        except sqlite3.Error as error:
            logger.error(f"Error fetching detailed data for topic_id {topic_id}: {str(error)}")
            return None
        finally:
            conn.close()