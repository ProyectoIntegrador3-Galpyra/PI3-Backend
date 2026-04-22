import pytest


PNG_VALIDO = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd4n\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.asyncio
async def test_inventario_procesar_acepta_campo_imagen(
    client,
    seeded_galpon_lote,
    auth_headers,
):
    lote = seeded_galpon_lote["lote"]

    response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        files={"imagen": ("inventario.png", PNG_VALIDO, "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["job_id"]
