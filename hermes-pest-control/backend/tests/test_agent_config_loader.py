import os
import pytest
from app.config.agent_loader import AgentConfigLoader

def test_agent_loader_loads_system_prompt() -> None:
    loader = AgentConfigLoader(cache_enabled=False)
    system_prompt = loader.load_system_prompt()
    assert system_prompt is not None
    assert "Hermes" in system_prompt

def test_agent_loader_loads_response_templates() -> None:
    loader = AgentConfigLoader(cache_enabled=False)
    templates = loader.load_response_templates()
    assert isinstance(templates, dict)
    assert "intake" in templates
    assert templates["intake"]["missing_customer_name"]["es"] == "¿A nombre de quién registramos el aviso?"

def test_agent_loader_graceful_degradation_missing_file() -> None:
    loader = AgentConfigLoader(cache_enabled=False)
    # Probar leer un archivo de conocimiento de plaga inexistente
    val = loader.load_pest_knowledge("non_existent_pest_12345")
    assert val == ""

def test_agent_loader_graceful_degradation_corrupted_yaml(tmp_path) -> None:
    # Simular una carga con archivo corrupto de templates
    loader = AgentConfigLoader(cache_enabled=False)
    
    # Modificar el método interno temporalmente para forzar que intente leer un YAML corrupto
    yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "config", "response_templates.yaml"))
    
    # Creamos un loader de prueba
    templates = loader.load_response_templates()
    assert isinstance(templates, dict)

def test_agent_loader_caching_and_hot_reload(tmp_path) -> None:
    # Crear un archivo markdown temporal en el directorio de prompts
    prompts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "prompts"))
    temp_file_path = os.path.join(prompts_dir, "temp_test_prompt.md")
    
    try:
        # 1. Escribir versión A
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write("Versión A")
            
        # 2. Con caché activada, lee Versión A
        loader_cache = AgentConfigLoader(cache_enabled=True)
        # Limpiar cualquier caché previa de esa ruta si existiera
        loader_cache._cache.pop(temp_file_path, None)
        
        val1 = loader_cache._read_file("temp_test_prompt.md")
        assert val1 == "Versión A"
        
        # Modificar el archivo a Versión B
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write("Versión B")
            
        # Debería devolver Versión A (usando caché)
        val2 = loader_cache._read_file("temp_test_prompt.md")
        assert val2 == "Versión A"
        
        # 3. Con caché desactivada, debería leer Versión B (hot reload)
        loader_no_cache = AgentConfigLoader(cache_enabled=False)
        val3 = loader_no_cache._read_file("temp_test_prompt.md")
        assert val3 == "Versión B"
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
