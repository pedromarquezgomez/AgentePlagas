import os
import glob
import shutil

def main():
    project_skills_dir = "/Users/pedro/AgentePlagas /hermes-pest-control/hermes/skills"
    hermes_skills_dir = os.path.expanduser("~/.hermes/skills")
    
    # Directorio de nuestra categoría personalizada "pest-control" en las skills de Hermes
    pest_control_dir = os.path.join(hermes_skills_dir, "pest-control")
    
    # 1. Limpiar cualquier enlace suelto que hayamos creado en la raíz de ~/.hermes/skills/ en el intento anterior
    pattern_md = os.path.join(hermes_skills_dir, "*.md")
    for old_link in glob.glob(pattern_md):
        if os.path.islink(old_link):
            try:
                os.remove(old_link)
                print(f"Limpiado enlace antiguo: {os.path.basename(old_link)}")
            except Exception:
                pass

    os.makedirs(pest_control_dir, exist_ok=True)
    
    # Buscar todos los archivos .md en el directorio de skills de nuestro proyecto
    pattern = os.path.join(project_skills_dir, "*.md")
    project_skills = glob.glob(pattern)
    
    print(f"Vinculando {len(project_skills)} skills en la estructura jerárquica de Nous...")
    for src_path in project_skills:
        filename = os.path.basename(src_path)
        skill_name = os.path.splitext(filename)[0] # e.g. "02_pest_control_domain"
        
        # Estructura: ~/.hermes/skills/pest-control/{skill_name}/SKILL.md
        skill_folder = os.path.join(pest_control_dir, skill_name)
        os.makedirs(skill_folder, exist_ok=True)
        
        dest_path = os.path.join(skill_folder, "SKILL.md")
        
        # Si ya existe un archivo o enlace, eliminarlo antes de crear el symlink
        if os.path.lexists(dest_path):
            try:
                if os.path.isdir(dest_path) and not os.path.islink(dest_path):
                    shutil.rmtree(dest_path)
                else:
                    os.remove(dest_path)
            except Exception as e:
                print(f"No se pudo eliminar {dest_path}: {e}")
                continue
                
        # Crear symlink
        try:
            os.symlink(src_path, dest_path)
            print(f"  Enlazado: pest-control/{skill_name}/SKILL.md -> {filename}")
        except Exception as e:
            print(f"  Error al enlazar {skill_name}: {e}")

if __name__ == "__main__":
    main()
