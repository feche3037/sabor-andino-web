"""Pruebas de comprobantes, carga diferida, anticipos y cuentas (HU10–HU16)."""

from datetime import date, timedelta
from decimal import Decimal
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from inicio.pruebas_base import BaseSaborAndino
from productores.models import Productor
from .models import Anticipo, Comprobante


class AcopioTests(BaseSaborAndino):
    def cargar(self, rol="acopiador", **extra):
        self.como(rol)
        datos = {"productor": self.productor.pk, "procedencia": "", "producto": self.pimenton.pk,
                 "kilos_brutos": "120", "tara": "5", "humedad": "12"}
        datos.update(extra)
        return self.client.post(reverse("acopio:nuevo"), datos)

    # ----------------------------------------------------------- HU10
    def test_registra_comprobante_con_calculos(self):
        r = self.cargar()
        c = Comprobante.objects.get()
        self.assertRedirects(r, c.get_absolute_url())
        self.assertEqual(c.numero, "2026-00001")
        self.assertEqual(c.kilos_netos, Decimal("115.00"))
        self.assertEqual(c.importe, Decimal("327750.00"))  # 115 kg × $ 2850
        self.assertEqual(c.procedencia, "Cachi")
        self.assertEqual(c.fecha_pago, timezone.localdate() + timedelta(days=30))
        self.assertEqual(c.registrado_por, self.usuarios["acopiador"])

    def test_numeros_correlativos_y_permanentes(self):
        self.cargar()
        self.cargar(rol="compras")
        self.assertEqual(list(Comprobante.objects.order_by("correlativo").values_list("numero", flat=True)), ["2026-00001", "2026-00002"])

    def test_datos_invalidos_no_se_guardan(self):
        self.assertContains(self.cargar(tara="130"), "La tara tiene que ser menor")
        self.cargar(humedad="105")
        self.assertEqual(Comprobante.objects.count(), 0)

    def test_sin_precio_de_referencia(self):
        r = self.cargar(producto=self.comino.pk)
        self.assertContains(r, "No hay precio de referencia de Comino")
        self.assertEqual(Comprobante.objects.count(), 0)

    def test_productor_inactivo_no_se_puede_elegir(self):
        Productor.objects.filter(pk=self.productor.pk).update(activo=False)
        self.cargar()
        self.assertEqual(Comprobante.objects.count(), 0)

    def test_gerencia_y_administracion_no_registran(self):
        for rol in ("gerencia", "administracion"):
            self.assertEqual(self.cargar(rol=rol).status_code, 403)

    # ----------------------------------------------------------- HU11 carga diferida
    def test_carga_diferida_conserva_numero_y_fecha_del_papel(self):
        entrega = (timezone.localtime() - timedelta(days=3)).replace(second=0, microsecond=0)
        self.cargar(carga_diferida="on", numero_papel="0457", fecha_entrega=entrega.strftime("%Y-%m-%dT%H:%M"))
        c = Comprobante.objects.get()
        self.assertTrue(c.carga_diferida)
        self.assertEqual(c.numero_papel, "0457")
        self.assertEqual(timezone.localtime(c.fecha_entrega), entrega)
        self.assertEqual(c.fecha_pago, entrega.date() + timedelta(days=30))

    def test_carga_diferida_valida_papel_y_fecha(self):
        futuro = (timezone.localtime() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self.assertContains(self.cargar(carga_diferida="on", numero_papel=""), "Indicá el número del comprobante en papel")
        self.assertContains(self.cargar(carga_diferida="on", numero_papel="1", fecha_entrega=futuro), "no puede ser futura")
        ayer = (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self.cargar(carga_diferida="on", numero_papel="0458", fecha_entrega=ayer)
        self.assertContains(self.cargar(carga_diferida="on", numero_papel="0458", fecha_entrega=ayer), "ya fue cargado")
        self.assertEqual(Comprobante.objects.count(), 1)

    # ----------------------------------------------------------- HU12
    def test_compras_anula_con_motivo(self):
        self.cargar()
        c = Comprobante.objects.get()
        self.como("acopiador")
        self.assertEqual(self.client.post(reverse("acopio:anular", args=[c.pk]), {"motivo": "Error de carga"}).status_code, 403)
        self.como("compras")
        self.client.post(reverse("acopio:anular", args=[c.pk]), {"motivo": "no"})
        c.refresh_from_db()
        self.assertEqual(c.estado, "registrado")
        self.client.post(reverse("acopio:anular", args=[c.pk]), {"motivo": "Kilos mal cargados"})
        c.refresh_from_db()
        self.assertEqual((c.estado, c.anulado_por), ("anulado", self.usuarios["compras"]))
        self.cargar()
        self.assertTrue(Comprobante.objects.filter(numero="2026-00002").exists())  # el 00001 no se reutiliza

    # ----------------------------------------------------------- HU13
    def test_anticipo_y_aviso_de_repetido(self):
        self.como("compras")
        datos = {"productor": self.productor.pk, "fecha": date.today().isoformat(), "importe": "50000", "autorizado_por": "R. Zerpa", "observacion": ""}
        self.client.post(reverse("acopio:nuevo_anticipo"), datos)
        r = self.client.post(reverse("acopio:nuevo_anticipo"), datos)
        self.assertContains(r, "Ya hay un anticipo igual")
        self.assertEqual(Anticipo.objects.count(), 1)
        self.client.post(reverse("acopio:nuevo_anticipo"), {**datos, "confirmar_repetido": "on"})
        self.assertEqual(Anticipo.objects.count(), 2)
        self.assertEqual(Anticipo.objects.first().registrado_por, self.usuarios["compras"])

    # ----------------------------------------------------------- HU14–HU16
    def test_cuenta_del_productor(self):
        self.cargar()
        self.cargar()
        self.como("compras")
        self.client.post(reverse("acopio:anular", args=[Comprobante.objects.get(numero="2026-00002").pk]), {"motivo": "Duplicado"})
        Anticipo.objects.create(campania=self.campania, productor=self.productor, fecha=date.today(), importe=Decimal("100000"),
                                autorizado_por="R. Zerpa", registrado_por=self.usuarios["compras"])
        self.como("administracion")
        r = self.client.get(reverse("acopio:cuenta", args=[self.productor.pk]))
        self.assertEqual(r.context["c"]["total_importe"], Decimal("327750.00"))  # el anulado no suma
        self.assertEqual(r.context["c"]["saldo"], Decimal("227750.00"))
        self.como("acopiador")
        self.assertEqual(self.client.get(reverse("acopio:cuenta", args=[self.productor.pk])).status_code, 403)

    def test_listado_por_periodo_y_saldos(self):
        self.cargar()
        otro = Productor.objects.create(nombre="Ana", apellido="Mamaní", dni_cuit="27999888", localidad="Seclantás",
                                        creado_por=self.admin, actualizado_por=self.admin)
        self.como("gerencia")
        hoy = date.today().isoformat()
        r = self.client.get(reverse("acopio:listado"), {"desde": hoy, "hasta": hoy})
        self.assertEqual(r.context["totales"]["kilos"], Decimal("115.00"))
        r = self.client.get(reverse("acopio:listado"), {"desde": hoy, "hasta": hoy, "productor": otro.pk})
        self.assertEqual(len(r.context["comprobantes"]), 0)
        r = self.client.get(reverse("acopio:saldos"))
        self.assertEqual([f["productor"] for f in r.context["filas"]], [self.productor])

    def test_inicio_para_cada_rol_y_datos_de_ejemplo(self):
        for rol in ("gerencia", "administracion", "compras", "acopiador", "admin"):
            self.como(rol)
            self.assertEqual(self.client.get(reverse("inicio:home")).status_code, 200)
        call_command("cargar_demo", usuario="admin")
        call_command("cargar_demo", usuario="admin")  # se puede repetir sin duplicar
        self.assertEqual(Productor.objects.filter(apellido__endswith="(DEMO)").count(), 3)
