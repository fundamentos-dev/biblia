# Test configuration
pytest_plugins = []

# Test markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: marca testes unitários"
    )
    config.addinivalue_line(
        "markers", "integration: marca testes de integração" 
    )
    config.addinivalue_line(
        "markers", "slow: marca testes que demoram mais para executar"
    )