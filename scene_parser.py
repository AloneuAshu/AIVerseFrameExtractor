import re

class Scene:
    def __init__(self, header, location, time_of_day, setting, dialogue="", action=""):
        self.header       = header
        self.location     = location
        self.time_of_day  = time_of_day
        self.setting      = setting
        self.dialogue     = dialogue   # list of (speaker, line) tuples
        self.action       = action
        self.shot_type    = "MEDIUM SHOT"
        self.camera_movement = "STATIC"
        self.lighting     = "NATURAL"

class ScriptParser:
    # Matches SCENE / INT. / EXT. / ACT / SHOT header lines
    HEADER_RE = re.compile(r'^(INT\.|EXT\.|SCENE|ACT|SHOT)\b.*$', re.MULTILINE | re.IGNORECASE)
    # Matches dialogue blocks: ALL-CAPS character name followed by a line of speech
    DIALOGUE_RE = re.compile(r'^([A-Z][A-Z\s\.\-\']+?)(?:\s*\(.*?\))?\s*\n(.*?)(?=\n[A-Z]|\Z)', re.MULTILINE | re.DOTALL)

    @staticmethod
    def parse_text(text):
        lines      = text.split('\n')
        scenes     = []
        current    = None
        buf        = []

        for line in lines:
            ls = line.strip()
            if not ls:
                buf.append("")
                continue

            if ScriptParser.HEADER_RE.match(ls):
                # Save previous scene
                if current:
                    raw = "\n".join(buf).strip()
                    current.action   = ScriptParser._extract_action(raw)
                    current.dialogue = ScriptParser._extract_dialogue(raw)
                    ScriptParser._enrich_scene(current)
                    scenes.append(current)
                    buf = []

                # Parse header
                upper = ls.upper()
                setting = "EXT." if "EXT." in upper else ("INT." if "INT." in upper else "UNKNOWN")
                parts   = re.split(r'[-–—:]', ls, 1)
                loc     = parts[0].strip()
                tod     = parts[1].strip() if len(parts) > 1 else "DAY"
                current = Scene(ls, loc, tod, setting)
            else:
                if current:
                    buf.append(ls)
                else:
                    current = Scene("PROLOGUE", "UNKNOWN", "DAY", "UNKNOWN")
                    buf.append(ls)

        if current:
            raw = "\n".join(buf).strip()
            current.action   = ScriptParser._extract_action(raw)
            current.dialogue = ScriptParser._extract_dialogue(raw)
            ScriptParser._enrich_scene(current)
            scenes.append(current)

        return scenes

    @staticmethod
    def _extract_dialogue(text):
        """Extract (speaker, line) pairs from raw scene text."""
        dialogues = []
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # A character name: ALL CAPS, short, not a direction
            if (line.isupper() and 2 <= len(line.split()) <= 5
                    and not any(line.startswith(k) for k in ["INT.", "EXT.", "CUT", "FADE", "DISSOLVE"])):
                speaker = line
                # Collect speech lines until blank or next cap name
                speech_lines = []
                i += 1
                while i < len(lines):
                    sl = lines[i].strip()
                    if not sl:
                        i += 1
                        break
                    # Parenthetical direction — skip
                    if sl.startswith("(") and sl.endswith(")"):
                        i += 1
                        continue
                    # Next character name → stop
                    if sl.isupper() and 2 <= len(sl.split()) <= 5:
                        break
                    speech_lines.append(sl)
                    i += 1
                if speech_lines:
                    dialogues.append((speaker, " ".join(speech_lines)))
            else:
                i += 1
        return dialogues

    @staticmethod
    def _extract_action(text):
        """Return only the action/description lines (non-dialogue)."""
        lines  = text.split('\n')
        action = []
        skip_next = False
        for line in lines:
            ls = line.strip()
            if not ls:
                continue
            # Skip dialogue character names and their lines
            if ls.isupper() and 2 <= len(ls.split()) <= 5:
                skip_next = True
                continue
            if skip_next and (ls.startswith('"') or ls[0].islower() or ls.startswith("(")):
                continue
            skip_next = False
            action.append(ls)
        return "\n".join(action)

    @staticmethod
    def _enrich_scene(scene):
        text = (scene.header + " " + scene.action).upper()

        # Shot type
        if any(w in text for w in ["CLOSE UP", "CLOSE-UP", " CU ", "PORTRAIT"]):
            scene.shot_type = "CLOSE UP"
        elif any(w in text for w in ["WIDE", "ESTABLISHING", "SKYLINE", "AERIAL", "BIRD"]):
            scene.shot_type = "WIDE SHOT"
        else:
            scene.shot_type = "MEDIUM SHOT"

        # Camera
        if "PAN"    in text: scene.camera_movement = "PAN"
        elif "TILT" in text: scene.camera_movement = "TILT"
        elif any(w in text for w in ["TRACK", "FOLLOW", "DOLLY"]): scene.camera_movement = "TRACKING"

        # Lighting
        if any(w in text for w in ["NIGHT", "DARK", "BURNING", "FIRE", "TORCH"]):
            scene.lighting = "DRAMATIC"
        elif any(w in text for w in ["SUNSET", "DUSK", "GOLDEN"]):
            scene.lighting = "GOLDEN HOUR"
        elif any(w in text for w in ["GRAY", "ASH", "OVERCAST", "STORM"]):
            scene.lighting = "OVERCAST"
        elif any(w in text for w in ["FLASH", "NUCLEAR", "BLAST", "EXPLOSION"]):
            scene.lighting = "EXTREME BACKLIGHT"
