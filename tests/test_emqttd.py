testinfra_hosts = ['concentrator1', 'concentrator2', 'concentrator3']

def test_installed(host):
    assert host.package("emqttd").is_installed
    assert host.service("emqttd").is_enabled

def test_health(host):
    assert host.service("emqttd").is_running
    assert host.socket("tcp://0.0.0.0:1883").is_listening
    assert host.socket("tcp://127.0.0.1:8081").is_listening
    assert not host.socket("tcp://0.0.0.0:8081").is_listening
