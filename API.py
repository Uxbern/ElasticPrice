import streamlit as st
import pandas as pd
import os
from elasticity_pipeline import ElasticityPipeline, COLUMN_NAMES
import tempfile

def save_uploaded_file(uploaded_file):
    """Sauvegarde le fichier téléchargé dans un emplacement temporaire et renvoie le chemin"""
    if uploaded_file is not None:
        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, uploaded_file.name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return path
    return None

def main():
    st.set_page_config(
        page_title="Dashboard d'Analyse d'Élasticité Prix",
        page_icon="image.jpg",
        layout="wide"
    )

    # En-tête
    st.title("Dashboard d'Analyse d'Élasticité Prix")
    st.markdown("""
    Cet outil permet d'analyser l'élasticité prix et de prédire la demande en fonction des changements de prix.
    Téléchargez vos fichiers d'entrée et visualisez les résultats de l'analyse.
    """)

    # Barre latérale
    st.sidebar.header("Documentation")
    with st.sidebar.expander("Format des Fichiers Requis"):
        st.markdown("""
        **indicators1.csv doit contenir:**
        - PRODUCT_ID
        - PRIX_TTC
        - PREVISION_J1 (Demande)

        **indicators2.csv doit contenir:**
        - PRODUCT_ID
        - Delta_P (Variation de Prix)
        - Sales_J_1 (Ventes J-1 ou les Ventes J-7/7) 
        
        Les deux fichiers doivent utiliser le point-virgule (;) comme séparateur.
        """)

    # Section Téléchargement de Fichiers
    st.header("1. Données d'Entrée")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Télécharger les Données Historiques")
        indicators1_file = st.file_uploader(
            "Télécharger indicators1.csv",
            type=['csv'],
            help="Données historiques de prix et de demande"
        )

    with col2:
        st.subheader("Télécharger les Données de Variation de Prix")
        indicators2_file = st.file_uploader(
            "Télécharger indicators2.csv",
            type=['csv'],
            help="Nouvelles variations de prix à analyser"
        )

    # Traitement des Données
    if indicators1_file and indicators2_file:
        try:
            # Sauvegarde des fichiers téléchargés
            indicators1_path = save_uploaded_file(indicators1_file)
            indicators2_path = save_uploaded_file(indicators2_file)

            # Initialisation du pipeline
            pipeline = ElasticityPipeline(indicators1_path, indicators2_path)

            # Bouton pour lancer l'analyse
            if st.button("Lancer l'Analyse"):
                with st.spinner("Traitement des données en cours..."):
                    # Exécution du pipeline complet
                    pipeline.run_pipeline()

                    # Affichage des Résultats
                    st.header("2. Résultats de l'Analyse")

                    # Afficher les Données Étendues
                    st.subheader("Résultats de la Régression de la Demande")
                    extended_df = pd.read_csv(pipeline.extended_output_path, sep=';')
                    st.dataframe(extended_df)
                    
                    # Afficher les Prédictions Finales
                    st.subheader("Prédictions Finales de la Demande")
                    final_df = pd.read_csv(pipeline.final_output_path, sep=';')
                    
                    # Créer un résumé plus visuel
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Variation Moyenne des Prix",
                            f"{final_df[COLUMN_NAMES['delta_price']].mean():.2f}%"
                        )
                    
                    with col2:
                        avg_elasticity = final_df['Applied_Elasticity'].mean()
                        st.metric(
                            "Élasticité Moyenne",
                            f"{avg_elasticity:.2f}"
                        )
                    
                    with col3:
                        demand_change = ((final_df['Predicted_Demand'].sum() / 
                                        final_df['Original_Demand'].sum() - 1) * 100)
                        st.metric(
                            "Variation Totale de la Demande",
                            f"{demand_change:.2f}%"
                        )

                    # Tableau détaillé des résultats
                    st.dataframe(final_df)

                    # Boutons de téléchargement
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        with open(pipeline.extended_output_path, 'rb') as file:
                            st.download_button(
                                "Télécharger les Résultats de Régression",
                                file,
                                file_name="resultats_regression.csv",
                                mime="text/csv"
                            )
                    
                    with col2:
                        with open(pipeline.elasticity_output_path, 'rb') as file:
                            st.download_button(
                                "Télécharger les Matrices d'Élasticité",
                                file,
                                file_name="matrices_elasticite.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
                    with col3:
                        with open(pipeline.final_output_path, 'rb') as file:
                            st.download_button(
                                "Télécharger les Prédictions Finales",
                                file,
                                file_name="predictions_finales.csv",
                                mime="text/csv"
                            )

        except Exception as e:
            st.error(f"Une erreur s'est produite: {str(e)}")
            st.error("Veuillez vérifier vos fichiers d'entrée et réessayer.")
        
        finally:
            # Nettoyage des fichiers temporaires
            if 'indicators1_path' in locals():
                os.remove(indicators1_path)
            if 'indicators2_path' in locals():
                os.remove(indicators2_path)

    # Section d'aide
    with st.expander("Besoin d'Aide ?"):
        st.markdown("""
        ### Comment Utiliser ce Dashboard

        1. **Préparer Vos Données**
           - Assurez-vous que vos fichiers d'entrée sont au format CSV avec séparateur point-virgule (;)
           - Vérifiez que toutes les colonnes requises sont présentes

        2. **Télécharger les Fichiers**
           - Téléchargez indicators1.csv et indicators2.csv
           - Attendez que les deux fichiers soient complètement téléchargés

        3. **Lancer l'Analyse**
           - Cliquez sur le bouton "Lancer l'Analyse"
           - Attendez que le traitement soit terminé

        4. **Examiner les Résultats**
           - Consultez les résultats de régression et les prédictions finales
           - Téléchargez les fichiers de sortie pour une analyse plus approfondie

        ### Problèmes Fréquents

        - Assurez-vous que vos fichiers CSV utilisent le point-virgule (;) comme séparateur
        - Vérifiez que les valeurs numériques utilisent la virgule (,) comme séparateur décimal
        - Vérifiez que toutes les colonnes requises sont présentes dans vos fichiers d'entrée
        """)

if __name__ == "__main__":
    main()
    
    
if __name__ == "__main__":
    main()