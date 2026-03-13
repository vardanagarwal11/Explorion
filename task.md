# Fix Explorion Bugs

## Bug 1: Middle videos not playing (only first & last work)
- [/] Investigate video URL generation in [process_visualization](file:///c:/Users/varda/OneDrive/Desktop/RESEARCH%20PAPER%20VISUALIZER/Explorion/backend/rendering/__init__.py#58-92) / [get_video_path](file:///c:/Users/varda/OneDrive/Desktop/RESEARCH%20PAPER%20VISUALIZER/Explorion/backend/rendering/storage.py#52-60)
- [ ] Check video file serving endpoint
- [ ] Verify `section_video_map` construction in [routes.py](file:///c:/Users/varda/OneDrive/Desktop/RESEARCH%20PAPER%20VISUALIZER/Explorion/backend/api/routes.py)
- [ ] Identify root cause and fix

## Bug 2: Audio not matching the videos
- [/] Check how `audio_url`/`subtitle_url` are mapped to sections in API response
- [ ] Verify TTS generation links audio to correct visualization
- [ ] Fix audio/subtitle mapping in API response

## Bug 3: Non-arXiv content (GitHub, technical) not working
- [ ] Test the `/api/process/universal` endpoint
- [ ] Check GitHub ingestion pipeline
- [ ] Check technical content ingestion pipeline
- [ ] Identify and fix failures

## Verification
- [ ] Test all three fixes end-to-end
