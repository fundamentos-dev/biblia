import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.database import engine
from app.models.Biblia import Versao, Livro, Versiculo

"""
ARA.json foi baixado de https://github.com/damarals/biblias
"""

# Mapeamento completo das abreviações JSON -> DB
ABBREV_MAPPING = {
    # Antigo Testamento
    "Gn": "Gn",        # Genesis
    "Êx": "Ex",        # Exodo  
    "Lv": "Lv",        # Levitico
    "Nm": "Nm",        # Numeros
    "Dt": "Dt",        # Deuteronomio
    "Js": "Js",        # Josue
    "Jz": "Jz",        # Juizes
    "Rt": "Rt",        # Rute
    "1Sm": "1Sm",      # I Samuel
    "2Sm": "2Sm",      # II Samuel
    "1Rs": "1Rs",      # I Reis
    "2Rs": "2Rs",      # II Reis
    "1Cr": "1Cr",      # I Cronicas
    "2Cr": "2Cr",      # II Cronicas
    "Ed": "Ed",        # Esdras
    "Ne": "Ne",        # Neemias
    "Et": "Et",        # Ester
    "Jó": "Jó",        # Jó
    "Sl": "Sl",        # Salmos
    "Pv": "Pv",        # Proverbios
    "Ec": "Ec",        # Eclesiastes
    "Ct": "Ct",        # Canticos
    "Is": "Is",        # Isaias
    "Jr": "Jr",        # Jeremias
    "Lm": "Lm",        # Lamentacoes
    "Ez": "Ez",        # Ezequiel
    "Dn": "Dn",        # Daniel
    "Os": "Os",        # Oseias
    "Jl": "Jl",        # Joel
    "Am": "Am",        # Amos
    "Ob": "Ob",        # Obadias
    "Jn": "Jn",        # Jonas
    "Mq": "Mq",        # Miqueias
    "Na": "Na",        # Naum
    "Hc": "Hc",        # Habacuque
    "Sf": "Sf",        # Sofonias
    "Ag": "Ag",        # Ageu
    "Zc": "Zc",        # Zacarias
    "Ml": "Ml",        # Malaquias
    
    # Novo Testamento
    "Mt": "Mt",        # Mateus
    "Mc": "Mc",        # Marcos
    "Lc": "Lc",        # Lucas
    "Jo": "Jo",        # João
    "At": "At",        # Atos
    "Rm": "Rm",        # Romanos
    "1Co": "1Co",      # I Corintios
    "2Co": "2Co",      # II Corintios
    "Gl": "Gl",        # Galatas
    "Ef": "Ef",        # Efesios
    "Fp": "Fp",        # Filipenses
    "Cl": "Cl",        # Colossenses
    "1Ts": "1Ts",      # I Tessalonicenses
    "2Ts": "2Ts",      # II Tessalonicenses
    "1Tn": "1Tm",      # I Timoteo
    "2Tm": "2Tm",      # II Timoteo
    "Tt": "Tt",        # Tito
    "Fm": "Fm",        # Filemom
    "Hb": "Hb",        # Hebreus
    "Tg": "Tg",        # Tiago
    "1Pe": "1Pe",      # I Pedro
    "2Pe": "2Pe",      # II Pedro
    "1Jo": "1Jo",      # I João
    "2Jo": "2Jo",      # II João
    "3Jo": "3Jo",      # III João
    "Jd": "Jd",        # Judas
    "Ap": "Ap"         # Apocalipse
}

def import_ara_json():
    """
    Importa os dados do ARA.json para o banco de dados.
    Cria uma nova versão ARA ativa com os versículos do JSON.
    """
    json_path = Path("/src/ARA.json")
    
    print("🔄 Iniciando importação do ARA.json...")
    
    # Carregar dados do JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            ara_data = json.load(f)
        print(f"📖 Carregados {len(ara_data)} livros do JSON")
    except Exception as e:
        print(f"❌ Erro ao carregar JSON: {e}")
        return
    
    with Session(engine) as session:
        # Buscar versão ARA existente para verificar
        versao_ara_existente = session.exec(
            select(Versao).where(Versao.abrev == "ARA")
        ).first()
        
        if not versao_ara_existente:
            print("❌ Versão ARA não encontrada no banco")
            return
            
        print(f"📋 Versão ARA encontrada: {versao_ara_existente.nome} (Active: {versao_ara_existente.active})")
        
        # Criar nova versão ARA ativa
        nova_versao = Versao(
            nome="Almeida Revista e Atualizada",
            abrev="ARA", 
            active=True
        )
        session.add(nova_versao)
        session.commit()
        session.refresh(nova_versao)
        
        print(f"✅ Nova versão ARA criada (ID: {nova_versao.id})")
        
        total_versiculos = 0
        livros_processados = 0
        
        for livro_data in ara_data:
            json_abbrev = livro_data["abbrev"]
            db_abbrev = ABBREV_MAPPING.get(json_abbrev)
            
            if not db_abbrev:
                print(f"⚠️  Abreviação '{json_abbrev}' não encontrada no mapeamento")
                continue
                
            # Buscar livro no banco
            livro = session.exec(
                select(Livro).where(Livro.abrev == db_abbrev)
            ).first()
            
            if not livro:
                print(f"❌ Livro com abreviação '{db_abbrev}' não encontrado no banco")
                continue
                
            print(f"📚 Processando {livro.nome} ({json_abbrev} -> {db_abbrev})")
            
            # Processar capítulos
            capitulos = livro_data["chapters"]
            versiculos_livro = 0
            
            for cap_num, capitulo in enumerate(capitulos, 1):
                for vers_num, texto in enumerate(capitulo, 1):
                    # Criar versículo
                    versiculo = Versiculo(
                        capitulo=cap_num,
                        numero=vers_num,
                        texto=texto.strip(),
                        livro_id=livro.id,
                        versao_id=nova_versao.id
                    )
                    session.add(versiculo)
                    total_versiculos += 1
                    versiculos_livro += 1
                    
                    # Commit em lotes para melhor performance
                    if total_versiculos % 1000 == 0:
                        session.commit()
                        print(f"   💾 Processados {total_versiculos} versículos...")
                        
            print(f"   ✅ {livro.nome}: {len(capitulos)} capítulos, {versiculos_livro} versículos")
            livros_processados += 1
                        
        # Commit final
        session.commit()
        
        print(f"\n🎉 Importação concluída!")
        print(f"📊 Estatísticas:")
        print(f"   • Livros processados: {livros_processados}/66")
        print(f"   • Total de versículos: {total_versiculos}")
        print(f"   • Nova versão ID: {nova_versao.id}")

def verificar_importacao():
    """
    Verifica a integridade dos dados importados.
    """
    print("\n🔍 Verificando importação...")
    
    with Session(engine) as session:
        # Buscar nova versão ARA ativa
        nova_versao = session.exec(
            select(Versao).where(Versao.abrev == "ARA").where(Versao.active == True)
        ).first()
        
        if not nova_versao:
            print("❌ Nova versão ARA ativa não encontrada")
            return
            
        # Contar versículos importados
        total_versiculos = session.exec(
            select(Versiculo).where(Versiculo.versao_id == nova_versao.id)
        ).all()
        
        print(f"✅ Verificação concluída:")
        print(f"   • Versão: {nova_versao.nome}")
        print(f"   • Versículos importados: {len(total_versiculos)}")
        
        # Verificar alguns versículos conhecidos
        genesis_1_1 = session.exec(
            select(Versiculo, Livro).
            where(Versiculo.versao_id == nova_versao.id).
            where(Versiculo.livro_id == Livro.id).
            where(Livro.abrev == "Gn").
            where(Versiculo.capitulo == 1).
            where(Versiculo.numero == 1)
        ).first()
        
        if genesis_1_1:
            print(f"   • Gênesis 1:1: {genesis_1_1[0].texto[:50]}...")

if __name__ == "__main__":
    try:
        import_ara_json()
        verificar_importacao()
    except Exception as e:
        print(f"❌ Erro durante importação: {e}")
        import traceback
        traceback.print_exc()