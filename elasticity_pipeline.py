import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import math
import logging
from typing import Tuple, List
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Définition des noms de colonnes standardisés
COLUMN_NAMES = {
    'product_id': 'PRODUCT_ID',
    'price': 'PRIX_TTC',
    'demand': 'PREVISION_J1',
    'delta_price': 'Delta_P',
    'current_sales': 'Sales_J_1',
    # Colonnes intermédiaires
    'elasticity': 'Elasticity',
    'price_i': 'P_i',
    'price_j': 'P_j',
    'demand_i': 'Q_i',
    'demand_j': 'Q_j',
    'delta_p_rel': 'Delta_P_rel',
    'index_i': 'i',
    'index_j': 'j'
}

class ElasticityPipeline:
    def __init__(self, indicators1_path: str, indicators2_path: str):
        """
        Initialise le pipeline avec les chemins des fichiers d'entrée.
        """
        self.indicators1_path = indicators1_path
        self.indicators2_path = indicators2_path
        self.extended_output_path = "output_extended.csv"
        self.elasticity_output_path = "elasticity_matrices.xlsx"
        self.final_output_path = "final_demand_predictions.csv"

    def validate_input_file(self, df: pd.DataFrame, required_columns: List[str], file_name: str):
        """
        Valide que toutes les colonnes requises sont présentes dans le DataFrame.
        """
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Colonnes manquantes dans {file_name}: {', '.join(missing_columns)}")
        logging.info(f"Validation des colonnes réussie pour {file_name}")

    def run_pipeline(self):
        """
        Exécute le pipeline complet d'analyse.
        """
        try:
            # Étape 1: Régression de la demande
            logging.info("Démarrage de la régression de la demande...")
            self._run_demand_regression()
            logging.info("Régression de la demande terminée")

            # Étape 2: Calcul des élasticités
            logging.info("Démarrage du calcul des élasticités...")
            self._calculate_elasticities()
            logging.info("Calcul des élasticités terminé")

            # Étape 3: Prédiction de la nouvelle demande
            logging.info("Démarrage de la prédiction de la nouvelle demande...")
            self._predict_new_demand()
            logging.info("Pipeline terminé avec succès")

        except Exception as e:
            logging.error(f"Erreur dans le pipeline: {str(e)}")
            raise

    def _run_demand_regression(self):
        """
        Exécute la régression de la demande (Script 1).
        """
        # Lecture du fichier d'entrée
        df = pd.read_csv(self.indicators1_path, sep=';', 
                        dtype={COLUMN_NAMES['product_id']: str}, 
                        decimal=',', 
                        na_values=['', 'NaN', 'nan', None])

        # Validation des colonnes requises
        required_columns = [COLUMN_NAMES['product_id'], 
                          COLUMN_NAMES['price'], 
                          COLUMN_NAMES['demand']]
        self.validate_input_file(df, required_columns, "indicators1.csv")

        # Nettoyage et préparation des données
        df[COLUMN_NAMES['price']] = df[COLUMN_NAMES['price']].astype(str).str.replace(',', '.')
        df[COLUMN_NAMES['price']] = pd.to_numeric(df[COLUMN_NAMES['price']], errors='coerce')
        df[COLUMN_NAMES['demand']] = pd.to_numeric(df[COLUMN_NAMES['demand']], errors='coerce')
        df.dropna(subset=required_columns, inplace=True)
        df = df[df[COLUMN_NAMES['demand']] > 0]

        # Traitement par groupe de produits
        extended_data = []
        for product_id, group in df.groupby(COLUMN_NAMES['product_id']):
            extended_group = self._process_product_group(group)
            extended_data.append(extended_group)

        # Concatenation et sauvegarde
        extended_df = pd.concat(extended_data, ignore_index=True)
        extended_df = extended_df.sort_values(by=[COLUMN_NAMES['product_id'], 
                                                COLUMN_NAMES['price']])
        extended_df.to_csv(self.extended_output_path, index=False, sep=';', decimal='.')

    def _process_product_group(self, group: pd.DataFrame) -> pd.DataFrame:
        """
        Traite un groupe de produits pour la régression.
        """
        valid_group = group.dropna(subset=[COLUMN_NAMES['price'], 
                                         COLUMN_NAMES['demand']])
        
        if len(valid_group) < 2:
            return valid_group

        # Régression log-linéaire
        P = valid_group[COLUMN_NAMES['price']].values.reshape(-1, 1)
        Q = valid_group[COLUMN_NAMES['demand']].values
        lnQ = np.log(Q)

        model = LinearRegression()
        model.fit(P, lnQ)

        # Génération de nouveaux prix
        min_price = valid_group[COLUMN_NAMES['price']].min()
        max_price = valid_group[COLUMN_NAMES['price']].max()
        lower_prices, upper_prices = self._generate_psycho_prices(min_price, max_price)
        new_prices = lower_prices + upper_prices

        # Prédiction des nouvelles demandes
        lnQ_pred = model.predict(np.array(new_prices).reshape(-1, 1))
        Q_pred = np.exp(lnQ_pred)

        # Création des nouvelles lignes
        new_rows = pd.DataFrame({
            COLUMN_NAMES['product_id']: group[COLUMN_NAMES['product_id']].iloc[0],
            COLUMN_NAMES['price']: new_prices,
            COLUMN_NAMES['demand']: Q_pred
        })

        return pd.concat([valid_group, new_rows], ignore_index=True)

    def _calculate_elasticities(self):
        """
        Calcule les élasticités (Script 2).
        """
        df = pd.read_csv(self.extended_output_path, sep=";")
        
        # Validation des colonnes requises
        required_columns = [COLUMN_NAMES['product_id'], 
                          COLUMN_NAMES['price'], 
                          COLUMN_NAMES['demand']]
        self.validate_input_file(df, required_columns, "output_extended.csv")

        df[COLUMN_NAMES['price']] = df[COLUMN_NAMES['price']].astype(float)
        df[COLUMN_NAMES['demand']] = df[COLUMN_NAMES['demand']].astype(float)

        with pd.ExcelWriter(self.elasticity_output_path, engine='xlsxwriter') as writer:
            for pid in df[COLUMN_NAMES['product_id']].unique():
                self._process_elasticity_for_product(df, pid, writer)

    def _process_elasticity_for_product(self, df: pd.DataFrame, pid: str, writer):
        """
        Calcule l'élasticité pour un produit spécifique.
        """
        product_df = df[df[COLUMN_NAMES['product_id']] == pid]
        prices = product_df[COLUMN_NAMES['price']].values
        demands = product_df[COLUMN_NAMES['demand']].values

        if len(prices) < 2:
            empty_df = pd.DataFrame(columns=[
                COLUMN_NAMES['index_i'], COLUMN_NAMES['index_j'],
                COLUMN_NAMES['price_i'], COLUMN_NAMES['price_j'],
                COLUMN_NAMES['delta_p_rel'],
                COLUMN_NAMES['demand_i'], COLUMN_NAMES['demand_j'],
                COLUMN_NAMES['elasticity']
            ])
            empty_df.to_excel(writer, sheet_name=str(pid), index=False)
            return

        i_idx = np.arange(len(prices))
        j_idx = np.arange(len(prices))
        i_grid, j_grid = np.meshgrid(i_idx, j_idx, indexing='ij')

        P_i = prices[i_grid]
        P_j = prices[j_grid]
        Q_i = demands[i_grid]
        Q_j = demands[j_grid]

        with np.errstate(divide='ignore', invalid='ignore'):
            elasticity_matrix = ((Q_j - Q_i) / Q_i) / ((P_j - P_i) / P_i)

        elasticity_matrix = np.where(np.isfinite(elasticity_matrix), 
                                   elasticity_matrix, np.nan)

        output_df = pd.DataFrame({
            COLUMN_NAMES['index_i']: i_grid.flatten(),
            COLUMN_NAMES['index_j']: j_grid.flatten(),
            COLUMN_NAMES['price_i']: P_i.flatten(),
            COLUMN_NAMES['price_j']: P_j.flatten(),
            COLUMN_NAMES['delta_p_rel']: (P_j.flatten() - P_i.flatten()) / P_i.flatten(),
            COLUMN_NAMES['demand_i']: Q_i.flatten(),
            COLUMN_NAMES['demand_j']: Q_j.flatten(),
            COLUMN_NAMES['elasticity']: elasticity_matrix.flatten()
        })

        output_df.sort_values([COLUMN_NAMES['index_i'], 
                             COLUMN_NAMES['index_j']], inplace=True)
        output_df.to_excel(writer, sheet_name=str(pid), index=False)

    def _predict_new_demand(self):
        """
        Prédit la nouvelle demande basée sur les élasticités calculées (Script 3).
        """
        # Lecture des données d'entrée
        indicators2 = pd.read_csv(self.indicators2_path, sep=';')
        
        # Validation des colonnes requises pour indicators2
        required_columns = [COLUMN_NAMES['product_id'], 
                          COLUMN_NAMES['delta_price'], 
                          COLUMN_NAMES['current_sales']]
        self.validate_input_file(indicators2, required_columns, "indicators2.csv")

        elasticities = pd.read_excel(self.elasticity_output_path, sheet_name=None)

        results = []
        for pid in indicators2[COLUMN_NAMES['product_id']].unique():
            if str(pid) in elasticities:
                product_elasticities = elasticities[str(pid)]
                delta_p = indicators2[indicators2[COLUMN_NAMES['product_id']] == pid][COLUMN_NAMES['delta_price']].iloc[0]
                
                # Trouver l'élasticité la plus proche
                product_elasticities['Delta_P_diff'] = abs(product_elasticities[COLUMN_NAMES['delta_p_rel']] - delta_p)
                closest_elasticity = product_elasticities.loc[product_elasticities['Delta_P_diff'].idxmin()]
                
                # Calculer la nouvelle demande
                current_demand = indicators2[indicators2[COLUMN_NAMES['product_id']] == pid][COLUMN_NAMES['current_sales']].iloc[0]
                elasticity = closest_elasticity[COLUMN_NAMES['elasticity']]
                new_demand = current_demand * (1 + elasticity * delta_p)
                
                results.append({
                    COLUMN_NAMES['product_id']: pid,
                    'Original_Demand': current_demand,
                    COLUMN_NAMES['delta_price']: delta_p,
                    'Applied_Elasticity': elasticity,
                    'Predicted_Demand': new_demand
                })

        # Sauvegarder les résultats
        pd.DataFrame(results).to_csv(self.final_output_path, index=False, sep=';')

    def _generate_psycho_prices(self, min_price: float, max_price: float) -> Tuple[List[float], List[float]]:
        """
        Génère des prix psychologiques autour des prix min et max.
        """
        lower_prices = [(math.floor(min_price) - i) + 0.99 for i in range(1, 4)]
        upper_prices = [(math.floor(max_price) + i) + 0.99 for i in range(1, 4)]
        return lower_prices, upper_prices

if __name__ == "__main__":
    # Chemins des fichiers d'entrée
    INDICATORS1_PATH = "indicateurs1.csv"
    INDICATORS2_PATH = "indicateurs2.csv"

    # Exécution du pipeline
    pipeline = ElasticityPipeline(INDICATORS1_PATH, INDICATORS2_PATH)
    pipeline.run_pipeline()