"""
Lead Manager - Deduplication, Persistence, Export, Email Finding
"""

import json
import csv
import hashlib
import requests
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from datetime import datetime
import io

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from src.utils.models import Lead
from src.config import settings


class LeadManager:
    """Manages leads with deduplication, persistence, and enrichment."""

    def __init__(self, storage_path: str = "data/leads.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._seen_hashes: Set[str] = set()
        self._load_seen_hashes()

    def _generate_hash(self, lead: Lead) -> str:
        """Generate unique hash for a lead based on URL, title, and author."""
        url = lead.url or ""
        title = (lead.title or "").lower().strip()
        author = (lead.username or lead.author if hasattr(lead, 'author') else "") or ""
        if isinstance(author, str):
            author = author.lower().strip()
        else:
            author = ""
        unique_string = f"{url}|{title}|{author}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _load_seen_hashes(self):
        """Load previously seen lead hashes from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for lead_data in data.get('leads', []):
                        hash_str = lead_data.get('hash', '')
                        if hash_str:
                            self._seen_hashes.add(hash_str)
            except Exception:
                pass

    def deduplicate(self, leads: List[Lead]) -> List[Lead]:
        """Remove duplicate leads based on URL, title, and author."""
        unique_leads = []
        session_hashes = set()

        for lead in leads:
            lead_hash = self._generate_hash(lead)

            # Skip if already seen in storage or this session
            if lead_hash in self._seen_hashes or lead_hash in session_hashes:
                continue

            session_hashes.add(lead_hash)
            unique_leads.append(lead)

        return unique_leads

    def save_leads(self, leads: List[Lead]) -> int:
        """Save leads to JSON storage. Returns number of new leads saved."""
        existing_data = {'leads': [], 'last_updated': None}

        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    existing_data = json.load(f)
            except Exception:
                pass

        new_count = 0
        for lead in leads:
            lead_hash = self._generate_hash(lead)

            if lead_hash not in self._seen_hashes:
                lead_dict = lead.model_dump()
                lead_dict['hash'] = lead_hash
                lead_dict['saved_at'] = datetime.now().isoformat()
                # Set default CRM status for new leads
                lead_dict['status'] = 'new'
                # Convert datetime objects to strings
                if lead_dict.get('found_at'):
                    lead_dict['found_at'] = str(lead_dict['found_at'])
                if lead_dict.get('posted_at'):
                    lead_dict['posted_at'] = str(lead_dict['posted_at'])
                # Convert enum to string
                if lead_dict.get('source'):
                    lead_dict['source'] = str(lead_dict['source'].value) if hasattr(lead_dict['source'], 'value') else str(lead_dict['source'])
                if lead_dict.get('urgency'):
                    lead_dict['urgency'] = str(lead_dict['urgency'].value) if hasattr(lead_dict['urgency'], 'value') else str(lead_dict['urgency'])

                existing_data['leads'].append(lead_dict)
                self._seen_hashes.add(lead_hash)
                new_count += 1

        existing_data['last_updated'] = datetime.now().isoformat()
        existing_data['total_count'] = len(existing_data['leads'])

        with open(self.storage_path, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)

        return new_count

    def load_leads(self) -> List[Dict]:
        """Load all saved leads from storage."""
        if not self.storage_path.exists():
            return []

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                return data.get('leads', [])
        except Exception:
            return []

    def import_from_csv(self, csv_content: str) -> Dict:
        """Import leads from CSV content. Returns stats about import."""
        imported = 0
        duplicates = 0
        errors = 0

        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            existing_data = {'leads': [], 'last_updated': None}
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            for row in reader:
                try:
                    # Normalize keys to lowercase
                    row_lower = {k.lower().strip(): v for k, v in row.items()}

                    # Contact info
                    title = row_lower.get('title', row_lower.get('titulo', row_lower.get('name', row_lower.get('nombre', ''))))
                    url = row_lower.get('url', row_lower.get('link', row_lower.get('website', '')))
                    author = row_lower.get('author', row_lower.get('autor', row_lower.get('contact', row_lower.get('contacto', ''))))
                    email = row_lower.get('email', row_lower.get('correo', row_lower.get('e-mail', row_lower.get('mail', ''))))
                    phone = row_lower.get('phone', row_lower.get('telefono', row_lower.get('tel', row_lower.get('mobile', row_lower.get('celular', '')))))

                    # Company info
                    company = row_lower.get('company', row_lower.get('empresa', row_lower.get('organization', '')))
                    website = row_lower.get('website', row_lower.get('sitio web', row_lower.get('web', '')))

                    # Professional info
                    position = row_lower.get('position', row_lower.get('cargo', row_lower.get('job title', row_lower.get('puesto', ''))))
                    linkedin = row_lower.get('linkedin', row_lower.get('linkedin url', ''))
                    twitter_handle = row_lower.get('twitter', row_lower.get('x', ''))

                    # Location
                    location = row_lower.get('location', row_lower.get('ubicacion', row_lower.get('city', row_lower.get('ciudad', ''))))
                    country = row_lower.get('country', row_lower.get('pais', ''))

                    # Business info
                    industry = row_lower.get('industry', row_lower.get('industria', row_lower.get('sector', '')))
                    employees = row_lower.get('employees', row_lower.get('empleados', ''))
                    revenue = row_lower.get('revenue', row_lower.get('ingresos', ''))

                    # Content
                    content = row_lower.get('content', row_lower.get('contenido', row_lower.get('description', row_lower.get('descripcion', ''))))
                    notes = row_lower.get('notes', row_lower.get('notas', row_lower.get('comments', '')))

                    # Scoring
                    pain_score_raw = row_lower.get('pain_score', row_lower.get('pain', row_lower.get('score', row_lower.get('priority', 0))))
                    status = row_lower.get('status', row_lower.get('estado', 'new'))
                    tags_raw = row_lower.get('tags', row_lower.get('etiquetas', ''))

                    if not title and not url and not email and not phone and not company:
                        errors += 1
                        continue

                    unique_string = f"{url}|{str(title).lower().strip()}|{str(author).lower().strip()}|{str(email).lower().strip()}"
                    lead_hash = hashlib.md5(unique_string.encode()).hexdigest()

                    if lead_hash in self._seen_hashes:
                        duplicates += 1
                        continue

                    # Parse pain score
                    try:
                        pain_value = int(float(pain_score_raw)) if pain_score_raw else 0
                    except (ValueError, TypeError):
                        pain_value = 0

                    # Parse tags
                    tags_list = []
                    if tags_raw:
                        if isinstance(tags_raw, str):
                            tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]

                    # Create lead dict
                    lead_dict = {
                        # Contact info
                        'title': str(title) if title else '',
                        'author': str(author) if author else '',
                        'email': str(email) if email else '',
                        'phone': str(phone) if phone else '',
                        'url': str(url) if url else '',

                        # Company info
                        'company': str(company) if company else '',
                        'website': str(website) if website else '',

                        # Professional info
                        'position': str(position) if position else '',
                        'linkedin': str(linkedin) if linkedin else '',
                        'twitter': str(twitter_handle) if twitter_handle else '',

                        # Location
                        'location': str(location) if location else '',
                        'country': str(country) if country else '',

                        # Business info
                        'industry': str(industry) if industry else '',
                        'employees': str(employees) if employees else '',
                        'revenue': str(revenue) if revenue else '',

                        # Content
                        'content': str(content) if content else '',
                        'notes': str(notes) if notes else '',

                        # Scoring & Status
                        'pain_score': pain_value,
                        'status': str(status) if status else 'new',
                        'tags': tags_list,

                        # Meta
                        'source': row_lower.get('source', 'csv_import'),
                        'hash': lead_hash,
                        'saved_at': datetime.now().isoformat(),
                        'imported': True
                    }

                    existing_data['leads'].append(lead_dict)
                    self._seen_hashes.add(lead_hash)
                    imported += 1

                except Exception as e:
                    errors += 1
                    continue

            existing_data['last_updated'] = datetime.now().isoformat()
            existing_data['total_count'] = len(existing_data['leads'])

            with open(self.storage_path, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)

        except Exception as e:
            return {
                'imported': 0,
                'duplicates': 0,
                'errors': 1,
                'error_message': str(e)
            }

        return {
            'imported': imported,
            'duplicates': duplicates,
            'errors': errors
        }

    def get_excel_sheets(self, file_content: bytes) -> List[str]:
        """Get list of sheet names from an Excel file."""
        if not PANDAS_AVAILABLE:
            return []

        try:
            excel_file = pd.ExcelFile(io.BytesIO(file_content))
            return excel_file.sheet_names
        except Exception:
            return []

    def import_from_excel(self, file_content: bytes, sheet_names: List[str] = None) -> Dict:
        """
        Import leads from Excel file (supports multiple sheets).

        Args:
            file_content: Raw bytes of the Excel file
            sheet_names: List of sheet names to import. If None, imports all sheets.

        Returns:
            Dict with import statistics
        """
        if not PANDAS_AVAILABLE:
            return {
                'imported': 0,
                'duplicates': 0,
                'errors': 1,
                'error_message': 'Pandas not available. Please install pandas and openpyxl.'
            }

        total_imported = 0
        total_duplicates = 0
        total_errors = 0
        sheets_processed = []

        try:
            excel_file = pd.ExcelFile(io.BytesIO(file_content))
            available_sheets = excel_file.sheet_names

            # If no sheets specified, import all
            if sheet_names is None:
                sheet_names = available_sheets
            else:
                # Validate sheet names
                sheet_names = [s for s in sheet_names if s in available_sheets]

            if not sheet_names:
                return {
                    'imported': 0,
                    'duplicates': 0,
                    'errors': 1,
                    'error_message': 'No valid sheets found to import.'
                }

            # Load existing data
            existing_data = {'leads': [], 'last_updated': None}
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            # Process each sheet
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)

                    # Normalize column names (lowercase, strip whitespace)
                    df.columns = [str(col).lower().strip() for col in df.columns]

                    sheet_imported = 0
                    sheet_duplicates = 0
                    sheet_errors = 0

                    for _, row in df.iterrows():
                        try:
                            # Try to find common column names - Contact Info
                            title = self._get_column_value(row, ['title', 'titulo', 'name', 'nombre', 'company', 'empresa', 'business', 'negocio'])
                            url = self._get_column_value(row, ['url', 'link', 'website', 'sitio', 'web', 'pagina'])
                            author = self._get_column_value(row, ['author', 'autor', 'contact', 'contacto', 'person', 'persona', 'contact name', 'nombre contacto'])
                            email = self._get_column_value(row, ['email', 'correo', 'e-mail', 'mail', 'email address', 'correo electronico'])

                            # Phone numbers
                            phone = self._get_column_value(row, ['phone', 'telefono', 'tel', 'telephone', 'mobile', 'movil', 'celular', 'cell', 'phone number', 'numero telefono', 'whatsapp'])

                            # Company info
                            company = self._get_column_value(row, ['company', 'empresa', 'organization', 'organizacion', 'business', 'negocio', 'company name', 'nombre empresa'])

                            # Professional info
                            position = self._get_column_value(row, ['position', 'cargo', 'job title', 'titulo', 'role', 'rol', 'puesto', 'job', 'trabajo', 'title'])
                            linkedin = self._get_column_value(row, ['linkedin', 'linkedin url', 'linkedin profile', 'perfil linkedin'])
                            twitter_handle = self._get_column_value(row, ['twitter', 'x', 'twitter url', 'twitter handle', '@'])

                            # Location
                            location = self._get_column_value(row, ['location', 'ubicacion', 'city', 'ciudad', 'address', 'direccion', 'place', 'lugar'])
                            country = self._get_column_value(row, ['country', 'pais', 'nation', 'nacion'])

                            # Business info
                            industry = self._get_column_value(row, ['industry', 'industria', 'sector', 'category', 'categoria', 'vertical', 'niche', 'nicho'])
                            employees = self._get_column_value(row, ['employees', 'empleados', 'team size', 'tamano equipo', 'headcount', 'staff'])
                            revenue = self._get_column_value(row, ['revenue', 'ingresos', 'sales', 'ventas', 'facturacion', 'billing'])
                            website = self._get_column_value(row, ['website', 'sitio web', 'web', 'homepage', 'pagina web', 'domain', 'dominio'])

                            # Content
                            content = self._get_column_value(row, ['content', 'contenido', 'description', 'descripcion', 'bio', 'about', 'acerca'])
                            notes = self._get_column_value(row, ['notes', 'notas', 'comments', 'comentarios', 'observations', 'observaciones'])

                            # Scoring
                            pain_score = self._get_column_value(row, ['pain_score', 'pain', 'score', 'puntuacion', 'priority', 'prioridad', 'rating', 'calificacion'])
                            status = self._get_column_value(row, ['status', 'estado', 'stage', 'etapa', 'lead status', 'estado lead'])
                            tags = self._get_column_value(row, ['tags', 'etiquetas', 'labels', 'categories', 'categorias'])

                            # Skip empty rows
                            if not title and not url and not email and not phone and not company:
                                continue

                            # Generate hash for deduplication
                            unique_string = f"{url}|{str(title).lower().strip()}|{str(author).lower().strip()}|{str(email).lower().strip()}"
                            lead_hash = hashlib.md5(unique_string.encode()).hexdigest()

                            if lead_hash in self._seen_hashes:
                                sheet_duplicates += 1
                                continue

                            # Create lead dict
                            try:
                                pain_value = int(float(pain_score)) if pain_score else 0
                            except (ValueError, TypeError):
                                pain_value = 0

                            # Process tags
                            tags_list = []
                            if tags:
                                if isinstance(tags, str):
                                    tags_list = [t.strip() for t in tags.split(',') if t.strip()]
                                elif isinstance(tags, list):
                                    tags_list = tags

                            lead_dict = {
                                # Contact info
                                'title': str(title) if title else '',
                                'author': str(author) if author else '',
                                'email': str(email) if email else '',
                                'phone': str(phone) if phone else '',
                                'url': str(url) if url else '',

                                # Company info
                                'company': str(company) if company else '',
                                'website': str(website) if website else '',

                                # Professional info
                                'position': str(position) if position else '',
                                'linkedin': str(linkedin) if linkedin else '',
                                'twitter': str(twitter_handle) if twitter_handle else '',

                                # Location
                                'location': str(location) if location else '',
                                'country': str(country) if country else '',

                                # Business info
                                'industry': str(industry) if industry else '',
                                'employees': str(employees) if employees else '',
                                'revenue': str(revenue) if revenue else '',

                                # Content
                                'content': str(content) if content else '',
                                'notes': str(notes) if notes else '',

                                # Scoring & Status
                                'pain_score': pain_value,
                                'status': str(status) if status else 'new',
                                'tags': tags_list,

                                # Meta
                                'source': f'excel:{sheet_name}',
                                'hash': lead_hash,
                                'saved_at': datetime.now().isoformat(),
                                'imported': True,
                                'import_sheet': sheet_name
                            }

                            existing_data['leads'].append(lead_dict)
                            self._seen_hashes.add(lead_hash)
                            sheet_imported += 1

                        except Exception:
                            sheet_errors += 1
                            continue

                    total_imported += sheet_imported
                    total_duplicates += sheet_duplicates
                    total_errors += sheet_errors
                    sheets_processed.append({
                        'name': sheet_name,
                        'imported': sheet_imported,
                        'duplicates': sheet_duplicates,
                        'errors': sheet_errors
                    })

                except Exception as e:
                    total_errors += 1
                    sheets_processed.append({
                        'name': sheet_name,
                        'error': str(e)
                    })

            # Save updated data
            existing_data['last_updated'] = datetime.now().isoformat()
            existing_data['total_count'] = len(existing_data['leads'])

            with open(self.storage_path, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)

        except Exception as e:
            return {
                'imported': 0,
                'duplicates': 0,
                'errors': 1,
                'error_message': f'Error reading Excel file: {str(e)}'
            }

        return {
            'imported': total_imported,
            'duplicates': total_duplicates,
            'errors': total_errors,
            'sheets_processed': sheets_processed
        }

    def _get_column_value(self, row, possible_names: List[str]):
        """Get value from row trying multiple possible column names."""
        for name in possible_names:
            if name in row.index:
                value = row[name]
                # Handle NaN values
                if pd.isna(value):
                    continue
                return value
        return None

    def import_from_excel_mapped(self, file_content: bytes, sheet_names: List[str], field_mappings: Dict[str, str]) -> Dict:
        """
        Import leads from Excel with explicit field mappings.

        Args:
            file_content: Raw bytes of the Excel file
            sheet_names: List of sheet names to import
            field_mappings: Dict mapping CRM fields to column names (e.g., {'email': 'Email Address', 'name': 'Contact Name'})

        Returns:
            Dict with import statistics
        """
        if not PANDAS_AVAILABLE:
            return {'imported': 0, 'duplicates': 0, 'errors': 1, 'error_message': 'Pandas not available'}

        total_imported = 0
        total_duplicates = 0
        total_errors = 0

        try:
            excel_file = pd.ExcelFile(io.BytesIO(file_content))

            # Load existing data
            existing_data = {'leads': [], 'last_updated': None}
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            for sheet_name in sheet_names:
                if sheet_name not in excel_file.sheet_names:
                    continue

                df = pd.read_excel(excel_file, sheet_name=sheet_name)

                for _, row in df.iterrows():
                    try:
                        # Extract values using the explicit mappings
                        def get_mapped_value(field_key):
                            if field_key in field_mappings:
                                col_name = field_mappings[field_key]
                                if col_name in row.index:
                                    val = row[col_name]
                                    if pd.notna(val):
                                        return str(val).strip()
                            return ''

                        name = get_mapped_value('name')
                        email = get_mapped_value('email')
                        phone = get_mapped_value('phone')
                        company = get_mapped_value('company')
                        position = get_mapped_value('position')
                        website = get_mapped_value('website')
                        linkedin = get_mapped_value('linkedin')
                        location = get_mapped_value('location')
                        country = get_mapped_value('country')
                        industry = get_mapped_value('industry')
                        notes = get_mapped_value('notes')
                        source = get_mapped_value('source') or f'excel:{sheet_name}'
                        status = get_mapped_value('status') or 'new'

                        # Skip empty rows
                        if not name and not email and not phone and not company:
                            continue

                        # Generate hash for deduplication
                        unique_string = f"{email}|{name.lower()}|{phone}|{company.lower()}"
                        lead_hash = hashlib.md5(unique_string.encode()).hexdigest()

                        if lead_hash in self._seen_hashes:
                            total_duplicates += 1
                            continue

                        # Create lead dict
                        lead_dict = {
                            'title': name,
                            'author': name,
                            'email': email,
                            'phone': phone,
                            'company': company,
                            'position': position,
                            'website': website,
                            'linkedin': linkedin,
                            'location': location,
                            'country': country,
                            'industry': industry,
                            'notes': notes,
                            'source': source,
                            'status': status,
                            'pain_score': 0,
                            'url': website or linkedin or '',
                            'content': notes,
                            'hash': lead_hash,
                            'saved_at': datetime.now().isoformat(),
                            'imported': True,
                            'import_sheet': sheet_name
                        }

                        existing_data['leads'].append(lead_dict)
                        self._seen_hashes.add(lead_hash)
                        total_imported += 1

                    except Exception:
                        total_errors += 1

            # Save
            existing_data['last_updated'] = datetime.now().isoformat()
            existing_data['total_count'] = len(existing_data['leads'])

            with open(self.storage_path, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)

        except Exception as e:
            return {'imported': 0, 'duplicates': 0, 'errors': 1, 'error_message': str(e)}

        return {
            'imported': total_imported,
            'duplicates': total_duplicates,
            'errors': total_errors
        }

    def import_from_csv_mapped(self, csv_content: str, field_mappings: Dict[str, str]) -> Dict:
        """
        Import leads from CSV with explicit field mappings.

        Args:
            csv_content: CSV string content
            field_mappings: Dict mapping CRM fields to column names

        Returns:
            Dict with import statistics
        """
        imported = 0
        duplicates = 0
        errors = 0

        try:
            if not PANDAS_AVAILABLE:
                return {'imported': 0, 'duplicates': 0, 'errors': 1, 'error_message': 'Pandas not available'}

            df = pd.read_csv(io.StringIO(csv_content))

            existing_data = {'leads': [], 'last_updated': None}
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            for _, row in df.iterrows():
                try:
                    def get_mapped_value(field_key):
                        if field_key in field_mappings:
                            col_name = field_mappings[field_key]
                            if col_name in row.index:
                                val = row[col_name]
                                if pd.notna(val):
                                    return str(val).strip()
                        return ''

                    name = get_mapped_value('name')
                    email = get_mapped_value('email')
                    phone = get_mapped_value('phone')
                    company = get_mapped_value('company')
                    position = get_mapped_value('position')
                    website = get_mapped_value('website')
                    linkedin = get_mapped_value('linkedin')
                    location = get_mapped_value('location')
                    country = get_mapped_value('country')
                    industry = get_mapped_value('industry')
                    notes = get_mapped_value('notes')
                    source = get_mapped_value('source') or 'csv_import'
                    status = get_mapped_value('status') or 'new'

                    if not name and not email and not phone and not company:
                        continue

                    unique_string = f"{email}|{name.lower()}|{phone}|{company.lower()}"
                    lead_hash = hashlib.md5(unique_string.encode()).hexdigest()

                    if lead_hash in self._seen_hashes:
                        duplicates += 1
                        continue

                    lead_dict = {
                        'title': name,
                        'author': name,
                        'email': email,
                        'phone': phone,
                        'company': company,
                        'position': position,
                        'website': website,
                        'linkedin': linkedin,
                        'location': location,
                        'country': country,
                        'industry': industry,
                        'notes': notes,
                        'source': source,
                        'status': status,
                        'pain_score': 0,
                        'url': website or linkedin or '',
                        'content': notes,
                        'hash': lead_hash,
                        'saved_at': datetime.now().isoformat(),
                        'imported': True
                    }

                    existing_data['leads'].append(lead_dict)
                    self._seen_hashes.add(lead_hash)
                    imported += 1

                except Exception:
                    errors += 1

            existing_data['last_updated'] = datetime.now().isoformat()
            existing_data['total_count'] = len(existing_data['leads'])

            with open(self.storage_path, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)

        except Exception as e:
            return {'imported': 0, 'duplicates': 0, 'errors': 1, 'error_message': str(e)}

        return {
            'imported': imported,
            'duplicates': duplicates,
            'errors': errors
        }

    def get_stats(self) -> Dict:
        """Get statistics about saved leads."""
        leads = self.load_leads()

        if not leads:
            return {
                'total': 0,
                'by_source': {},
                'by_industry': {},
                'avg_pain_score': 0,
                'hot_leads': 0
            }

        by_source = {}
        by_industry = {}
        total_pain_score = 0
        hot_leads = 0

        for lead in leads:
            # Count by source
            source = lead.get('source', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1

            # Count by industry
            industry = lead.get('industry', 'Unknown')
            if industry:
                by_industry[industry] = by_industry.get(industry, 0) + 1

            # Pain score
            pain_score = lead.get('pain_score', 0)
            total_pain_score += pain_score
            if pain_score >= 70:
                hot_leads += 1

        return {
            'total': len(leads),
            'by_source': by_source,
            'by_industry': by_industry,
            'avg_pain_score': total_pain_score / len(leads) if leads else 0,
            'hot_leads': hot_leads
        }

    def update_lead(self, lead_hash: str, updates: Dict) -> bool:
        """
        Update a specific lead by its hash.

        Args:
            lead_hash: The hash of the lead to update
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully
        """
        if not self.storage_path.exists():
            return False

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            for lead in data.get('leads', []):
                if lead.get('hash') == lead_hash:
                    for key, value in updates.items():
                        lead[key] = value
                    lead['updated_at'] = datetime.now().isoformat()

                    with open(self.storage_path, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                    return True

            return False
        except Exception:
            return False

    def add_note_to_lead(self, lead_hash: str, note: str, author: str = "User") -> bool:
        """
        Add a note to a lead's activity history.

        Args:
            lead_hash: The hash of the lead
            note: The note text to add
            author: Who added the note

        Returns:
            True if added successfully
        """
        if not self.storage_path.exists():
            return False

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            for lead in data.get('leads', []):
                if lead.get('hash') == lead_hash:
                    if 'activity_log' not in lead:
                        lead['activity_log'] = []

                    lead['activity_log'].append({
                        'type': 'note',
                        'content': note,
                        'author': author,
                        'timestamp': datetime.now().isoformat()
                    })
                    lead['updated_at'] = datetime.now().isoformat()

                    with open(self.storage_path, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                    return True

            return False
        except Exception:
            return False

    def update_lead_status(self, lead_hash: str, new_status: str) -> bool:
        """
        Update a lead's pipeline status.

        Args:
            lead_hash: The hash of the lead
            new_status: New status (new, contacted, demo, proposal, won, lost)

        Returns:
            True if updated successfully
        """
        if not self.storage_path.exists():
            return False

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            for lead in data.get('leads', []):
                if lead.get('hash') == lead_hash:
                    old_status = lead.get('status', 'new')
                    lead['status'] = new_status
                    lead['updated_at'] = datetime.now().isoformat()

                    # Add to activity log
                    if 'activity_log' not in lead:
                        lead['activity_log'] = []

                    lead['activity_log'].append({
                        'type': 'status_change',
                        'from': old_status,
                        'to': new_status,
                        'timestamp': datetime.now().isoformat()
                    })

                    with open(self.storage_path, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                    return True

            return False
        except Exception:
            return False

    def get_lead_by_hash(self, lead_hash: str) -> Optional[Dict]:
        """Get a specific lead by its hash."""
        leads = self.load_leads()
        for lead in leads:
            if lead.get('hash') == lead_hash:
                return lead
        return None

    def get_leads_by_status(self, status: str) -> List[Dict]:
        """Get all leads with a specific status."""
        leads = self.load_leads()
        return [l for l in leads if l.get('status', 'new') == status]

    def delete_lead(self, lead_hash: str) -> bool:
        """Delete a lead from storage."""
        if not self.storage_path.exists():
            return False

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            original_count = len(data.get('leads', []))
            data['leads'] = [l for l in data.get('leads', []) if l.get('hash') != lead_hash]

            if len(data['leads']) < original_count:
                # Remove from seen hashes
                self._seen_hashes.discard(lead_hash)

                data['last_updated'] = datetime.now().isoformat()
                data['total_count'] = len(data['leads'])

                with open(self.storage_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                return True

            return False
        except Exception:
            return False

    def clear_storage(self):
        """Clear all saved leads."""
        self._seen_hashes.clear()
        if self.storage_path.exists():
            self.storage_path.unlink()

    def get_duplicate_count(self, leads: List[Lead]) -> int:
        """Count how many leads are duplicates."""
        duplicates = 0
        session_hashes = set()

        for lead in leads:
            lead_hash = self._generate_hash(lead)
            if lead_hash in self._seen_hashes or lead_hash in session_hashes:
                duplicates += 1
            else:
                session_hashes.add(lead_hash)

        return duplicates


class CSVExporter:
    """Export leads to CSV format."""

    # Complete field list for exports
    EXPORT_FIELDS = [
        # Contact info
        'title', 'author', 'email', 'phone', 'url',
        # Company info
        'company', 'website',
        # Professional info
        'position', 'linkedin', 'twitter',
        # Location
        'location', 'country',
        # Business info
        'industry', 'employees', 'revenue',
        # Scoring
        'pain_score', 'urgency', 'status',
        # Content
        'content_preview', 'notes',
        # Meta
        'source', 'tags', 'saved_at'
    ]

    @staticmethod
    def export_leads(leads: List[Lead]) -> str:
        """Export leads to CSV string."""
        output = io.StringIO()

        fieldnames = CSVExporter.EXPORT_FIELDS

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            # Handle tags
            tags_str = ''
            if hasattr(lead, 'tags') and lead.tags:
                tags_str = ', '.join(lead.tags) if isinstance(lead.tags, list) else str(lead.tags)

            writer.writerow({
                # Contact info
                'title': lead.title[:100] if lead.title else '',
                'author': getattr(lead, 'author', '') or getattr(lead, 'name', '') or '',
                'email': lead.email or '',
                'phone': getattr(lead, 'phone', '') or '',
                'url': lead.url or '',
                # Company info
                'company': getattr(lead, 'company', '') or '',
                'website': getattr(lead, 'website', '') or '',
                # Professional info
                'position': getattr(lead, 'position', '') or '',
                'linkedin': getattr(lead, 'linkedin', '') or '',
                'twitter': getattr(lead, 'twitter', '') or '',
                # Location
                'location': getattr(lead, 'location', '') or '',
                'country': getattr(lead, 'country', '') or '',
                # Business info
                'industry': lead.industry or '',
                'employees': getattr(lead, 'employees', '') or '',
                'revenue': getattr(lead, 'revenue', '') or '',
                # Scoring
                'pain_score': lead.pain_score,
                'urgency': lead.urgency.value if hasattr(lead.urgency, 'value') else str(lead.urgency),
                'status': getattr(lead, 'status', 'new') or 'new',
                # Content
                'content_preview': lead.content[:200] if lead.content else '',
                'notes': getattr(lead, 'notes', '') or '',
                # Meta
                'source': lead.source.value if hasattr(lead.source, 'value') else str(lead.source),
                'tags': tags_str,
                'saved_at': str(lead.found_at) if lead.found_at else ''
            })

        return output.getvalue()

    @staticmethod
    def export_leads_from_dict(leads: List[Dict]) -> str:
        """Export leads from dictionary format to CSV string."""
        output = io.StringIO()

        fieldnames = CSVExporter.EXPORT_FIELDS

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            # Handle tags
            tags = lead.get('tags', [])
            if isinstance(tags, list):
                tags_str = ', '.join(tags)
            else:
                tags_str = str(tags) if tags else ''

            writer.writerow({
                # Contact info
                'title': str(lead.get('title', ''))[:100],
                'author': lead.get('author', lead.get('name', '')),
                'email': lead.get('email', ''),
                'phone': lead.get('phone', ''),
                'url': lead.get('url', ''),
                # Company info
                'company': lead.get('company', ''),
                'website': lead.get('website', ''),
                # Professional info
                'position': lead.get('position', ''),
                'linkedin': lead.get('linkedin', ''),
                'twitter': lead.get('twitter', ''),
                # Location
                'location': lead.get('location', ''),
                'country': lead.get('country', ''),
                # Business info
                'industry': lead.get('industry', ''),
                'employees': lead.get('employees', ''),
                'revenue': lead.get('revenue', ''),
                # Scoring
                'pain_score': lead.get('pain_score', 0),
                'urgency': lead.get('urgency', ''),
                'status': lead.get('status', 'new'),
                # Content
                'content_preview': str(lead.get('content', ''))[:200],
                'notes': lead.get('notes', ''),
                # Meta
                'source': lead.get('source', ''),
                'tags': tags_str,
                'saved_at': lead.get('saved_at', '')
            })

        return output.getvalue()


class EmailFinder:
    """Find email addresses for leads using Hunter.io API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'hunter_api_key', None)
        self.base_url = "https://api.hunter.io/v2"

    def is_configured(self) -> bool:
        """Check if Hunter.io API is configured."""
        return bool(self.api_key)

    def find_email(self, domain: str, first_name: str = None, last_name: str = None) -> Optional[Dict]:
        """Find email for a person at a domain."""
        if not self.is_configured():
            return None

        try:
            params = {
                'domain': domain,
                'api_key': self.api_key
            }

            if first_name:
                params['first_name'] = first_name
            if last_name:
                params['last_name'] = last_name

            response = requests.get(
                f"{self.base_url}/email-finder",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('email'):
                    return {
                        'email': data['data']['email'],
                        'confidence': data['data'].get('score', 0),
                        'sources': data['data'].get('sources', [])
                    }
        except Exception:
            pass

        return None

    def verify_email(self, email: str) -> Optional[Dict]:
        """Verify if an email address is valid."""
        if not self.is_configured():
            return None

        try:
            response = requests.get(
                f"{self.base_url}/email-verifier",
                params={
                    'email': email,
                    'api_key': self.api_key
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('data', {}).get('status'),
                    'score': data.get('data', {}).get('score', 0),
                    'disposable': data.get('data', {}).get('disposable', False)
                }
        except Exception:
            pass

        return None

    def domain_search(self, domain: str, limit: int = 10) -> List[Dict]:
        """Search for all emails at a domain."""
        if not self.is_configured():
            return []

        try:
            response = requests.get(
                f"{self.base_url}/domain-search",
                params={
                    'domain': domain,
                    'api_key': self.api_key,
                    'limit': limit
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                emails = data.get('data', {}).get('emails', [])
                return [
                    {
                        'email': e.get('value'),
                        'first_name': e.get('first_name'),
                        'last_name': e.get('last_name'),
                        'position': e.get('position'),
                        'confidence': e.get('confidence', 0)
                    }
                    for e in emails
                ]
        except Exception:
            pass

        return []


# Singleton instances
lead_manager = LeadManager()
csv_exporter = CSVExporter()
email_finder = EmailFinder()
