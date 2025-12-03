import photo_manager
import os
import argparse

print("Generating map...")
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'data', 'photo_exif.db')
web_dir = os.path.join(script_dir, 'web')
output_dir = os.path.join(script_dir, 'output')

# Set up argument parser
parser = argparse.ArgumentParser(description="Generate a photo map HTML file.")
parser.add_argument('--template', type=str, 
                    help="Path to the HTML template file (e.g., web/map_template_en-US.html)")
parser.add_argument('--output', type=str, 
                    help="Path for the output HTML file (e.g., output/photo_map_en-US.html)")
args = parser.parse_args()

# Determine template path
if args.template:
    template_path = os.path.join(script_dir, args.template)
else:
    template_path = os.path.join(web_dir, 'map_template_zh-TW.html')

# Determine output path
if args.output:
    output_path = os.path.join(script_dir, args.output)
else:
    output_path = os.path.join(output_dir, 'photo_map.html')

# Ensure output directory exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

photo_manager.generate_map_non_interactive(db_path, template_path, output_path)
print("Map generation complete.")
