def test_clients_package_exports_yclientweb():
    from y_client.clients import YClientWeb

    assert YClientWeb is not None
