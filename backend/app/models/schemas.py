from pydantic import BaseModel, Field


class Image(BaseModel):
    url: str
    width: int | None = None
    height: int | None = None


class UserProfile(BaseModel):
    id: str
    display_name: str | None
    images: list[Image] = []
    total_playlists: int
    csrf_token: str


class PlaylistSummary(BaseModel):
    id: str
    name: str
    images: list[Image] = []
    owner: str
    owner_id: str | None = None
    tracks_total: int
    public: bool | None = None
    collaborative: bool = False
    tracks_readable: bool = True


class Track(BaseModel):
    id: str | None
    uri: str
    name: str
    artists: list[str]
    album: str
    album_art: str | None = None
    duration_ms: int
    added_at: str | None = None


class TrackPage(BaseModel):
    playlist_id: str
    tracks: list[Track]
    total: int
    offset: int
    limit: int
    next_offset: int | None
    has_more: bool
    artists: list[str] = []
    albums: list[str] = []


class CreatePlaylistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=300)
    public: bool = False


class TransferRequest(BaseModel):
    source_playlist_id: str
    destination_playlist_id: str
    track_uris: list[str] = Field(min_length=1)
    skip_duplicates: bool = True


class DuplicateSummary(BaseModel):
    duplicates: int
    new_tracks: int
    duplicate_uris: list[str]


class TransferResult(BaseModel):
    operation_id: str
    action: str
    requested: int
    transferred: int
    skipped_duplicates: int
    failures: list[str] = []
    duplicate_summary: DuplicateSummary


class UndoResult(BaseModel):
    restored: int
    action: str
    message: str
