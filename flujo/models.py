from django.db import models


class Concepto(models.Model):
    TIPO_INGRESO = "INGRESO"
    TIPO_EGRESO = "EGRESO"
    TIPO_FINANCIAMIENTO = "FINANCIAMIENTO"
    TIPO_EXCLUIR = "EXCLUIR"

    TIPO_CHOICES = [
        (TIPO_INGRESO, "Ingreso"),
        (TIPO_EGRESO, "Egreso operacional"),
        (TIPO_FINANCIAMIENTO, "Financiamiento"),
        (TIPO_EXCLUIR, "Excluir"),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CuentaBanco(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200, blank=True, default="")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Cuenta banco"
        verbose_name_plural = "Cuentas banco"

    def __str__(self):
        if self.nombre:
            return f"{self.codigo} - {self.nombre}"
        return self.codigo


class Movimiento(models.Model):
    cuenta_banco = models.ForeignKey(
        CuentaBanco,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    concepto = models.ForeignKey(
        Concepto,
        on_delete=models.PROTECT,
        related_name="movimientos",
        null=True,
        blank=True,
    )

    fecha = models.DateField()
    anio = models.IntegerField()
    mes = models.IntegerField()

    cpbnum = models.CharField(max_length=20, blank=True, default="")

    mov_debe = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    mov_haber = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    descripcion = models.CharField(max_length=500, blank=True, default="")
    cajcod = models.CharField(max_length=20, blank=True, default="")

    origen_clave = models.CharField(max_length=255, blank=True, default="", db_index=True)
    origen_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["fecha", "id"]

    @property
    def monto(self):
        return self.mov_debe - self.mov_haber

    def __str__(self):
        return f"{self.fecha} | {self.cuenta_banco.codigo} | {self.cpbnum} | {self.descripcion}"


class Proyeccion(models.Model):
    concepto = models.ForeignKey(
        Concepto,
        on_delete=models.PROTECT,
        related_name="proyecciones",
    )
    anio = models.IntegerField()
    mes = models.IntegerField()
    monto = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    descripcion = models.CharField(max_length=500, blank=True, default="")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["anio", "mes", "concepto__codigo", "id"]
        verbose_name = "Proyección"
        verbose_name_plural = "Proyecciones"

    def __str__(self):
        return f"{self.anio}-{self.mes:02d} | {self.concepto.codigo} | {self.monto}"