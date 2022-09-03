


from datetime import datetime


class Files:
    id: int
    path: str
    created_at: datetime
    last_accessed: datetime
    access_count: int

class Chapters:
    id: int
    file_id: int
    start: int
    end: int
    created_at: datetime
    last_accessed: datetime
    access_count: int

class Tags:
    id: int
    name: str


class ChapterTags:
    tag_id: int
    tag_name: str
    chapter_id: int

