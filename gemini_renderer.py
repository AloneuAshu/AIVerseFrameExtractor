"""
GeminiRenderer — Professional Masterpiece Storyboard Generation
Converts scene descriptions into high-fidelity AI-generated art using Gemini Imagen.
Tailored for professional pencil sketches and Gojo-style manga aesthetics.
"""
import os
import io
from PIL import Image

def build_prompt(scene_header: str, scene_action: str, style_name: str) -> str:
    """Creates a professional, high-fidelity 'Masterpiece' sketch prompt."""
    
    # Character Intelligence (Inject Gojo-style attributes)
    char_notes = ""
    upper_text = (scene_header + " " + scene_action).upper()
    
    if "RUDRAKHAN" in upper_text:
        char_notes += "Rudrakhan: Intense antagonist, spiky white Gojo-style hair, athletic build, high-collared dark jacket. "
    if "WOMAN" in upper_text or "SHE " in upper_text:
        char_notes += "The Woman: Defiant, wounded but strong, long flowing dark hair, tattered cinematic clothing. "
    
    # Core Masterpiece Prompt Structure
    prompt = (
        f"PROFESSIONAL STORYBOARD ART: {scene_header}. \n"
        f"ACTION: {scene_action}. \n"
        f"DESCRIPTION: {upper_text[:300]}. \n"
        f"STYLE: A masterpiece cinematic pencil sketch on slightly aged storyboard paper. "
        f"High-contrast charcoal shading, professional line art, dramatic lighting, detailed facial expressions. "
        f"NOT a simple doodle, NOT cartoonish. Highly realistic anatomical proportions. \n"
        f"ARTISTIC DIRECTION: {char_notes} Inspired by high-end manga key visuals. \n"
        f"Avoid any text, labels, or watermarks inside the frame. Ultra-detailed textures."
    )
    return prompt

def generate_image(api_key: str, prompt: str, output_path: str) -> bool:
    """Call the Gemini Imagen API and save the image. Returns True on success."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        # Using Imagen 4.0 for Masterpiece quality (found via list_models)
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="BLOCK_LOW_AND_ABOVE",
                person_generation="ALLOW_ADULT",
            ),
        )
        
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            img = Image.open(io.BytesIO(image_bytes))
            # Resize to standard production resolution
            img = img.resize((1920, 1080), Image.LANCZOS)
            img.save(output_path, quality=95)
            return True
        else:
            print("[GeminiRenderer] No images generated in response.")
            return False

    except Exception as e:
        print(f"[GeminiRenderer] Error calling Gemini API: {e}")
        return False

def inpaint_image(api_key: str, image_path: str, mask_path: str, output_path: str) -> bool:
    """Uses Gemini Imagen's 'edit_image' to remove objects in the mask area."""
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # Load images
        with open(image_path, "rb") as f:
            base_bytes = f.read()
        with open(mask_path, "rb") as f:
            mask_bytes = f.read()
            
        print(f"[GeminiRenderer] Calling edit_image (Inpaint Removal)...")
        response = client.models.edit_image(
            model="imagen-3.0-capability-001", # Standard editing model, or imagen-4.0
            prompt="Remove the object in the mask and inpaint the background perfectly.",
            config=types.EditImageConfig(
                edit_mode="EDIT_MODE_INPAINT_REMOVAL",
                number_of_images=1,
            ),
            reference_images=[
                types.RawReferenceImage(reference_id=1, image_bytes=base_bytes),
                types.MaskReferenceImage(reference_id=2, reference_image=types.RawReferenceImage(reference_id=1, image_bytes=base_bytes), mask_bytes=mask_bytes)
            ]
        )
        
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            img = Image.open(io.BytesIO(image_bytes))
            img.save(output_path, quality=95)
            return True
        return False
    except Exception as e:
        print(f"[GeminiRenderer] Inpaint Error: {e}")
        return False
