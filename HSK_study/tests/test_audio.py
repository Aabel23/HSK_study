def test_audio_requires_text_param(client):
    response = client.get("/api/audio")
    assert response.status_code == 422


def test_audio_rejects_invalid_voice(client):
    response = client.get("/api/audio", params={"text": "你好", "voice": "robot"})
    assert response.status_code == 422
