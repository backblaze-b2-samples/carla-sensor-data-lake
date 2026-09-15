export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- CARLA Sensor Data Lake ---

/** Create/edit payload for a Scenario (the primary entity). */
export interface ScenarioInput {
  name: string;
  description: string;
  town: string;
  weather: string;
  traffic_density: string;
  fps: number;
  frame_count: number;
  sensors: string[];
}

/** A stored Scenario: the input config plus server-assigned identity. */
export interface Scenario extends ScenarioInput {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface BBoxAnnotation {
  frame: number;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface EpisodeMetadata {
  id: string;
  scenario_id: string | null;
  scenario_name: string | null;
  town: string;
  weather: string;
  traffic_density: string;
  fps: number;
  requested_frames: number;
  captured_frames: number;
  sensors: string[];
  frames_by_sensor: Record<string, number>;
  status: string;
  /** "carla" (a real run) or "synthetic-seed" (demo data). */
  capture_source: string;
  error: string | null;
  annotations: BBoxAnnotation[];
  started_at: string;
  finished_at: string | null;
}

export interface EpisodeSummary {
  id: string;
  scenario_id: string | null;
  scenario_name: string | null;
  town: string;
  weather: string;
  status: string;
  capture_source: string;
  captured_frames: number;
  total_objects: number;
  size_bytes: number;
  size_human: string;
  created_at: string;
}

export interface EpisodeDetail {
  metadata: EpisodeMetadata;
  total_objects: number;
  size_bytes: number;
  size_human: string;
}

export interface SensorCount {
  sensor: string;
  frames: number;
}

export interface GroupCount {
  label: string;
  episodes: number;
}

export interface DailyFrameCount {
  date: string;
  frames: number;
}

export interface LakeStats {
  total_episodes: number;
  total_frames: number;
  total_scenarios: number;
  total_size_bytes: number;
  total_size_human: string;
  frames_by_sensor: SensorCount[];
  episodes_by_weather: GroupCount[];
  episodes_by_town: GroupCount[];
}
