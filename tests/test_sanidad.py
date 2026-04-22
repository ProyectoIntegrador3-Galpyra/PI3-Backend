from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_sanidad_acepta_nuevo_enum(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    payload = {
        "lote_id": lote.id,
        "galpon_id": galpon.id,
        "tipo_evento": "DIAGNOSTICO",
        "descripcion": "Diagnostico preventivo",
        "producto": "Vitamina",
        "dosis": "5ml",
        "responsable": "Tecnico",
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/api/sanidad", json=payload, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sanidad_rechaza_enum_antiguo(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    payload = {
        "lote_id": lote.id,
        "galpon_id": galpon.id,
        "tipo_evento": "ENFERMEDAD",
        "descripcion": "Valor antiguo",
        "producto": "Vitamina",
        "dosis": "5ml",
        "responsable": "Tecnico",
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/api/sanidad", json=payload, headers=auth_headers)
    assert response.status_code == 422
