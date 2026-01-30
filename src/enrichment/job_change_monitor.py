"""
Job Change Monitor - LinkedIn Job Change Detection Service

CONCEPTO:
Detectar cuando alguien cambia de trabajo (especialmente a puestos de liderazgo)
genera una ventana de oportunidad de 90 días donde hay 3x más probabilidad de compra.

SEÑALES VALIOSAS:
- Nuevo Director/VP/Gerente → Llegan con mandato de cambio y presupuesto
- Promoción interna → Quieren demostrar valor con nuevas iniciativas
- Nuevo CEO/Fundador → Construyendo equipo y procesos desde cero
- Cambio de industria → Traen ideas frescas, buscan nuevos proveedores

IMPLEMENTACIÓN:
Este módulo ofrece 3 estrategias:
1. Apollo.io API - Usa señales de "job change" y "new hire"
2. LinkedIn Sales Navigator - Alertas nativas (requiere licencia)
3. Monitoreo periódico - Guarda snapshots y detecta cambios

USO:
    monitor = JobChangeMonitor(apollo_api_key="xxx")

    # Monitorear empresas target
    opportunities = monitor.check_target_companies(["acme.com", "bigcorp.com"])

    # Buscar nuevos ejecutivos en industria
    new_leaders = monitor.find_new_leaders(industry="dental", titles=["director", "vp"])
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

import requests

from src.utils.models import Lead, LeadSource, LeadUrgency

logger = logging.getLogger(__name__)


class JobChangeType(str, Enum):
    """Tipos de cambio de trabajo detectados."""
    NEW_HIRE = "new_hire"           # Recién contratado en la empresa
    PROMOTION = "promotion"          # Promoción interna
    ROLE_CHANGE = "role_change"      # Cambio de rol (misma empresa)
    COMPANY_CHANGE = "company_change" # Cambió de empresa
    UNKNOWN = "unknown"


class OpportunityLevel(str, Enum):
    """Nivel de oportunidad del cambio."""
    GOLD = "gold"      # C-level, VP en empresa target - máxima prioridad
    SILVER = "silver"  # Director, Manager en empresa target
    BRONZE = "bronze"  # Otros cambios relevantes


@dataclass
class JobChange:
    """Representa un cambio de trabajo detectado."""

    # Identificación
    person_id: str
    linkedin_url: Optional[str] = None

    # Información de la persona
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Trabajo ANTERIOR
    previous_title: Optional[str] = None
    previous_company: Optional[str] = None
    previous_company_domain: Optional[str] = None

    # Trabajo NUEVO (actual)
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    current_company_domain: Optional[str] = None
    current_seniority: Optional[str] = None  # c_suite, vp, director, manager

    # Metadata del cambio
    change_type: JobChangeType = JobChangeType.UNKNOWN
    change_detected_at: datetime = field(default_factory=datetime.utcnow)
    days_in_role: int = 0

    # Clasificación
    opportunity_level: OpportunityLevel = OpportunityLevel.BRONZE
    opportunity_score: int = 0  # 0-100
    opportunity_reason: str = ""

    # Datos de empresa
    company_industry: Optional[str] = None
    company_employees: Optional[int] = None
    company_revenue: Optional[str] = None

    # Estado
    contacted: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización."""
        data = asdict(self)
        data['change_type'] = self.change_type.value
        data['opportunity_level'] = self.opportunity_level.value
        data['change_detected_at'] = self.change_detected_at.isoformat()
        return data

    def to_lead(self) -> Lead:
        """Convertir a objeto Lead para integrar con el pipeline existente."""

        # Construir contenido descriptivo
        content_parts = [
            f"Job Change Detected: {self.change_type.value}",
            f"Previous: {self.previous_title} at {self.previous_company}",
            f"Current: {self.current_title} at {self.current_company}",
            f"Days in new role: {self.days_in_role}",
            f"Opportunity: {self.opportunity_level.value.upper()} - {self.opportunity_reason}"
        ]

        return Lead(
            id=f"jobchange_{self.person_id}_{datetime.utcnow().strftime('%Y%m%d')}",
            source=LeadSource.LINKEDIN,

            # Contacto
            name=self.full_name or f"{self.first_name or ''} {self.last_name or ''}".strip(),
            email=self.email,
            phone=self.phone,
            company=self.current_company,
            website=self.current_company_domain,

            # Profesional
            position=self.current_title,
            linkedin=self.linkedin_url,

            # Contenido
            title=f"🚀 New {self.current_title} at {self.current_company}",
            content="\n".join(content_parts),
            url=self.linkedin_url or "",

            # Clasificación
            industry=self.company_industry,
            employees=str(self.company_employees) if self.company_employees else None,
            revenue=self.company_revenue,

            # Scoring alto para cambios de trabajo
            pain_score=0,  # No es pain, es oportunidad
            intent_score=self.opportunity_score,  # Alta intención implícita
            fit_score=self._calculate_fit_score(),
            total_score=self.opportunity_score,
            urgency=self._determine_urgency(),

            # Tags especiales
            keywords_matched=["job_change", self.change_type.value, self.opportunity_level.value],
            tags=["job_change_signal", f"days_{self.days_in_role}"],

            # Calificar automáticamente los cambios GOLD/SILVER
            is_qualified=self.opportunity_level in [OpportunityLevel.GOLD, OpportunityLevel.SILVER],
            ai_reasoning=self.opportunity_reason,

            extra_data={
                "job_change": self.to_dict()
            }
        )

    def _calculate_fit_score(self) -> int:
        """Calcular fit score basado en seniority y empresa."""
        score = 50  # Base

        # Bonus por seniority
        seniority_bonus = {
            "c_suite": 40,
            "vp": 35,
            "director": 25,
            "manager": 15,
            "senior": 10
        }
        if self.current_seniority:
            score += seniority_bonus.get(self.current_seniority.lower(), 0)

        # Bonus por tamaño de empresa
        if self.company_employees:
            if 10 <= self.company_employees <= 200:
                score += 10  # Sweet spot para SMB

        return min(100, score)

    def _determine_urgency(self) -> LeadUrgency:
        """Determinar urgencia basada en días en rol."""
        if self.days_in_role <= 30:
            return LeadUrgency.CRITICAL  # Primeros 30 días - máxima oportunidad
        elif self.days_in_role <= 60:
            return LeadUrgency.HIGH
        elif self.days_in_role <= 90:
            return LeadUrgency.MEDIUM
        else:
            return LeadUrgency.LOW


class JobChangeMonitor:
    """
    Monitor de cambios de trabajo para detectar oportunidades de venta.

    Estrategias disponibles:
    1. Apollo.io API - Señales de job change
    2. Monitoreo periódico - Guardar snapshots y comparar

    Ejemplo:
        monitor = JobChangeMonitor()

        # Opción 1: Buscar nuevos líderes en industria
        changes = monitor.find_new_leaders_in_industry(
            industry="dental",
            titles=["director", "manager", "owner"],
            max_days_in_role=90
        )

        # Opción 2: Monitorear empresas específicas
        changes = monitor.check_target_companies(
            domains=["dentalpractice.com", "smileclinic.com"]
        )

        # Convertir a leads para el pipeline
        leads = [change.to_lead() for change in changes]
    """

    APOLLO_BASE_URL = "https://api.apollo.io/v1"

    # Títulos que indican poder de decisión
    DECISION_MAKER_TITLES = [
        "owner", "founder", "ceo", "president", "principal",
        "director", "vp", "vice president", "head of",
        "manager", "chief", "partner"
    ]

    # Seniority levels de interés
    TARGET_SENIORITY = ["c_suite", "vp", "director", "manager", "owner", "founder"]

    def __init__(
        self,
        apollo_api_key: Optional[str] = None,
        storage_path: Optional[str] = None
    ):
        """
        Inicializar monitor.

        Args:
            apollo_api_key: API key de Apollo.io
            storage_path: Ruta para guardar snapshots (para monitoreo periódico)
        """
        self.apollo_api_key = apollo_api_key or os.getenv("APOLLO_API_KEY")
        self.storage_path = Path(storage_path or "data/job_changes")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        if self.apollo_api_key:
            self.session.headers.update({
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            })

    def is_configured(self) -> bool:
        """Verificar si Apollo está configurado."""
        return bool(self.apollo_api_key)

    def find_new_leaders_in_industry(
        self,
        industry: str,
        titles: Optional[List[str]] = None,
        max_days_in_role: int = 90,
        location: Optional[str] = None,
        company_size_min: int = 5,
        company_size_max: int = 500,
        limit: int = 50
    ) -> List[JobChange]:
        """
        Buscar personas que recientemente tomaron roles de liderazgo en una industria.

        Esta es la funcionalidad principal: encuentra decision-makers que acaban
        de llegar a su puesto y están en la "ventana de oportunidad" de 90 días.

        Args:
            industry: Industria objetivo (ej: "dental", "hvac", "legal")
            titles: Títulos a buscar (default: decision makers)
            max_days_in_role: Máximo días en el rol actual (default: 90)
            location: Filtro de ubicación (ej: "United States", "California")
            company_size_min: Mínimo empleados
            company_size_max: Máximo empleados
            limit: Máximo resultados

        Returns:
            Lista de JobChange con oportunidades detectadas
        """
        if not self.is_configured():
            logger.warning("Apollo API no configurada. Configura APOLLO_API_KEY.")
            return []

        titles = titles or self.DECISION_MAKER_TITLES
        job_changes = []

        try:
            # Apollo People Search con filtros
            payload = {
                "api_key": self.apollo_api_key,
                "q_keywords": industry,
                "person_titles": titles,
                "person_seniorities": self.TARGET_SENIORITY,
                "organization_num_employees_ranges": [f"{company_size_min},{company_size_max}"],
                "page": 1,
                "per_page": min(limit, 100)
            }

            if location:
                payload["person_locations"] = [location]

            response = self.session.post(
                f"{self.APOLLO_BASE_URL}/mixed_people/search",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                people = data.get("people", [])

                for person in people:
                    job_change = self._parse_apollo_person(person)

                    if job_change and job_change.days_in_role <= max_days_in_role:
                        # Calcular oportunidad
                        self._score_opportunity(job_change)
                        job_changes.append(job_change)

                logger.info(f"Encontrados {len(job_changes)} cambios de trabajo en {industry}")
            else:
                logger.error(f"Apollo API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error buscando cambios de trabajo: {e}")

        # Ordenar por score de oportunidad
        job_changes.sort(key=lambda x: x.opportunity_score, reverse=True)

        return job_changes

    def check_target_companies(
        self,
        domains: List[str],
        titles: Optional[List[str]] = None
    ) -> List[JobChange]:
        """
        Verificar cambios de trabajo en empresas específicas (target accounts).

        Útil para Account-Based Marketing: monitorear empresas específicas
        y detectar cuando llegan nuevos líderes.

        Args:
            domains: Lista de dominios de empresas a monitorear
            titles: Títulos de interés (default: decision makers)

        Returns:
            Lista de JobChange en las empresas monitoreadas
        """
        if not self.is_configured():
            logger.warning("Apollo API no configurada.")
            return []

        titles = titles or self.DECISION_MAKER_TITLES
        all_changes = []

        for domain in domains:
            try:
                payload = {
                    "api_key": self.apollo_api_key,
                    "q_organization_domains": domain,
                    "person_titles": titles,
                    "person_seniorities": self.TARGET_SENIORITY,
                    "page": 1,
                    "per_page": 25
                }

                response = self.session.post(
                    f"{self.APOLLO_BASE_URL}/mixed_people/search",
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    people = data.get("people", [])

                    for person in people:
                        job_change = self._parse_apollo_person(person)
                        if job_change:
                            # Para empresas target, 180 días aún es relevante
                            if job_change.days_in_role <= 180:
                                self._score_opportunity(job_change, is_target_account=True)
                                all_changes.append(job_change)

            except Exception as e:
                logger.error(f"Error verificando {domain}: {e}")

        all_changes.sort(key=lambda x: x.opportunity_score, reverse=True)
        return all_changes

    def detect_job_changes_from_snapshot(
        self,
        current_contacts: List[Dict[str, Any]],
        snapshot_name: str = "default"
    ) -> List[JobChange]:
        """
        Detectar cambios comparando con un snapshot anterior.

        Esta estrategia no requiere API de job changes - simplemente
        guarda snapshots periódicos y detecta diferencias.

        Args:
            current_contacts: Lista actual de contactos a verificar
            snapshot_name: Nombre del snapshot para comparar

        Returns:
            Lista de cambios detectados
        """
        snapshot_file = self.storage_path / f"{snapshot_name}_snapshot.json"

        # Cargar snapshot anterior
        previous_contacts = {}
        if snapshot_file.exists():
            with open(snapshot_file, 'r') as f:
                previous_data = json.load(f)
                previous_contacts = {c.get('linkedin_url', c.get('email', '')): c
                                    for c in previous_data.get('contacts', [])}

        changes = []

        for contact in current_contacts:
            contact_id = contact.get('linkedin_url') or contact.get('email', '')
            if not contact_id:
                continue

            if contact_id in previous_contacts:
                prev = previous_contacts[contact_id]

                # Detectar cambio de título
                if contact.get('title') != prev.get('title'):
                    change = JobChange(
                        person_id=contact_id,
                        linkedin_url=contact.get('linkedin_url'),
                        full_name=contact.get('name'),
                        email=contact.get('email'),
                        previous_title=prev.get('title'),
                        previous_company=prev.get('company'),
                        current_title=contact.get('title'),
                        current_company=contact.get('company'),
                        change_type=self._determine_change_type(prev, contact)
                    )
                    self._score_opportunity(change)
                    changes.append(change)

        # Guardar nuevo snapshot
        self._save_snapshot(current_contacts, snapshot_name)

        return changes

    def _parse_apollo_person(self, person: Dict[str, Any]) -> Optional[JobChange]:
        """Parsear respuesta de Apollo a JobChange."""
        try:
            employment = person.get("employment_history", [])
            current_job = employment[0] if employment else {}
            previous_job = employment[1] if len(employment) > 1 else {}

            org = person.get("organization", {})

            # Calcular días en rol actual
            start_date = current_job.get("start_date")
            days_in_role = 0
            if start_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    days_in_role = (datetime.utcnow() - start).days
                except:
                    pass

            # Determinar tipo de cambio
            change_type = JobChangeType.UNKNOWN
            if previous_job:
                if previous_job.get("organization_name") != org.get("name"):
                    change_type = JobChangeType.COMPANY_CHANGE
                elif current_job.get("title") != previous_job.get("title"):
                    # Simplificación: si el título cambió, asumimos promoción
                    change_type = JobChangeType.PROMOTION
            else:
                change_type = JobChangeType.NEW_HIRE

            return JobChange(
                person_id=person.get("id", ""),
                linkedin_url=person.get("linkedin_url"),
                first_name=person.get("first_name"),
                last_name=person.get("last_name"),
                full_name=f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                email=person.get("email"),
                phone=person.get("phone_numbers", [None])[0] if person.get("phone_numbers") else None,

                previous_title=previous_job.get("title"),
                previous_company=previous_job.get("organization_name"),

                current_title=person.get("title"),
                current_company=org.get("name"),
                current_company_domain=org.get("primary_domain"),
                current_seniority=person.get("seniority"),

                change_type=change_type,
                days_in_role=days_in_role,

                company_industry=org.get("industry"),
                company_employees=org.get("estimated_num_employees"),
                company_revenue=org.get("annual_revenue_printed")
            )

        except Exception as e:
            logger.error(f"Error parseando persona de Apollo: {e}")
            return None

    def _score_opportunity(
        self,
        change: JobChange,
        is_target_account: bool = False
    ) -> None:
        """
        Calcular score y nivel de oportunidad.

        Factores:
        - Seniority del nuevo rol (C-level > VP > Director > Manager)
        - Días en el rol (menos días = más oportunidad)
        - Tipo de cambio (company_change > promotion > new_hire)
        - Si es target account (bonus)
        """
        score = 0
        reasons = []

        # 1. Bonus por seniority (0-40 puntos)
        seniority_scores = {
            "c_suite": 40,
            "owner": 40,
            "founder": 40,
            "vp": 35,
            "director": 25,
            "manager": 15
        }
        seniority = (change.current_seniority or "").lower()
        for key, points in seniority_scores.items():
            if key in seniority or key in (change.current_title or "").lower():
                score += points
                reasons.append(f"{key.upper()} level = high decision power")
                break

        # 2. Bonus por días en rol (0-30 puntos)
        if change.days_in_role <= 30:
            score += 30
            reasons.append("First 30 days = peak opportunity window")
        elif change.days_in_role <= 60:
            score += 20
            reasons.append("Days 31-60 = high opportunity")
        elif change.days_in_role <= 90:
            score += 10
            reasons.append("Days 61-90 = moderate opportunity")

        # 3. Bonus por tipo de cambio (0-15 puntos)
        if change.change_type == JobChangeType.COMPANY_CHANGE:
            score += 15
            reasons.append("Changed companies = new vendor evaluation likely")
        elif change.change_type == JobChangeType.PROMOTION:
            score += 10
            reasons.append("Promoted = wants to make impact")

        # 4. Bonus por target account (0-15 puntos)
        if is_target_account:
            score += 15
            reasons.append("Target account match")

        # Determinar nivel
        if score >= 70:
            change.opportunity_level = OpportunityLevel.GOLD
        elif score >= 45:
            change.opportunity_level = OpportunityLevel.SILVER
        else:
            change.opportunity_level = OpportunityLevel.BRONZE

        change.opportunity_score = min(100, score)
        change.opportunity_reason = " | ".join(reasons)

    def _determine_change_type(
        self,
        prev: Dict[str, Any],
        current: Dict[str, Any]
    ) -> JobChangeType:
        """Determinar tipo de cambio entre dos snapshots."""
        prev_company = (prev.get("company") or "").lower()
        curr_company = (current.get("company") or "").lower()

        if prev_company != curr_company:
            return JobChangeType.COMPANY_CHANGE
        elif prev.get("title") != current.get("title"):
            return JobChangeType.ROLE_CHANGE
        return JobChangeType.UNKNOWN

    def _save_snapshot(self, contacts: List[Dict[str, Any]], name: str) -> None:
        """Guardar snapshot de contactos."""
        snapshot_file = self.storage_path / f"{name}_snapshot.json"
        with open(snapshot_file, 'w') as f:
            json.dump({
                "saved_at": datetime.utcnow().isoformat(),
                "contacts": contacts
            }, f, indent=2)
        logger.info(f"Snapshot guardado: {snapshot_file}")

    def get_opportunities_summary(
        self,
        changes: List[JobChange]
    ) -> Dict[str, Any]:
        """
        Generar resumen de oportunidades detectadas.

        Returns:
            Diccionario con estadísticas y recomendaciones
        """
        if not changes:
            return {"total": 0, "message": "No se detectaron cambios de trabajo"}

        gold = [c for c in changes if c.opportunity_level == OpportunityLevel.GOLD]
        silver = [c for c in changes if c.opportunity_level == OpportunityLevel.SILVER]
        bronze = [c for c in changes if c.opportunity_level == OpportunityLevel.BRONZE]

        return {
            "total": len(changes),
            "by_level": {
                "gold": len(gold),
                "silver": len(silver),
                "bronze": len(bronze)
            },
            "urgent": len([c for c in changes if c.days_in_role <= 30]),
            "top_opportunities": [
                {
                    "name": c.full_name,
                    "title": c.current_title,
                    "company": c.current_company,
                    "days_in_role": c.days_in_role,
                    "score": c.opportunity_score,
                    "linkedin": c.linkedin_url
                }
                for c in gold[:5]  # Top 5 GOLD
            ],
            "recommended_action": (
                f"🔥 {len(gold)} oportunidades GOLD detectadas. "
                f"Contactar en las próximas 24-48 horas para máximo impacto."
                if gold else
                f"📊 {len(silver)} oportunidades SILVER. Programar outreach esta semana."
                if silver else
                "🔍 Solo oportunidades BRONZE. Considerar agregar más empresas target."
            )
        }


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)

    # Crear monitor
    monitor = JobChangeMonitor()

    if monitor.is_configured():
        # Buscar nuevos líderes en industria dental
        changes = monitor.find_new_leaders_in_industry(
            industry="dental practice",
            titles=["owner", "director", "manager", "practice administrator"],
            max_days_in_role=90,
            location="United States",
            company_size_min=5,
            company_size_max=100
        )

        # Mostrar resumen
        summary = monitor.get_opportunities_summary(changes)
        print(json.dumps(summary, indent=2))

        # Convertir a leads para el pipeline
        leads = [change.to_lead() for change in changes]
        print(f"\n{len(leads)} leads generados listos para el pipeline")
    else:
        print("Configura APOLLO_API_KEY para usar el monitor")
