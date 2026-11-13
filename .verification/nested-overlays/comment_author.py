import json
from pathlib import Path
r=Path.cwd()
p={'recipes':[{'recipe_id':'explain-screen-overlay-order-owner','operations':[{'operation':'patch_target','file_path':str(r/'src/textual/_compositor.py'),'target_qualname':'Compositor._place_children','replacements':[{'old_source':'            yield (child, region, child_region,','new_source':'            # A screen overlay escapes its containing scene, including a\n            # containing screen overlay. Keep that nesting in the paint order.\n            yield (child, region, child_region,'}]}]}]}
Path('.verification/nested-overlays/comment.plan.json').write_text(json.dumps(p,indent=2))
