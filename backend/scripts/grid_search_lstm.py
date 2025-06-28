import itertools
import os
import torch
from algorithms.dl.sequence_classifier import draws_to_sequences, LottoLSTM, predict_next_numbers
from models import Draw
from logger import logger
from db import SessionLocal
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from config import TICKET_COST_PER_TABLE, PRIZE_TABLE, NUM_COMBINATIONS_TO_RECOMMEND, SEQUENCE_CLASSIFIER_MODEL_DIR
from datetime import date
import json
from services.simulation_helpers.simulation_utils import calculate_roi_with_tax

# --- Hyperparameter grid ---
hyperparams_grid = {
    'hidden_size': [64, 128, 256],
    'num_layers': [1, 2, 3],
    'seq_len': [10, 20],
    'lr': [0.001, 0.0005, 0.0003],
    'batch_size': [8, 16],
    'epochs': [20],  # For quick search; increase for best results
}

def load_draws():
    db = SessionLocal()
    try:
        draws = db.query(Draw).order_by(Draw.date).all()
        return draws
    finally:
        db.close()

def calculate_prize(hits, strong_hit):
    return PRIZE_TABLE.get((hits, strong_hit), 0)

def evaluate_model(draws, model_path, seq_len, strong_algo_cls):
    # Use last 12 draws as test set, rest as train
    if len(draws) < seq_len + 13:
        raise ValueError("Not enough draws for evaluation!")
    test_count = 12
    train_draws = draws[:-test_count]
    test_draws = draws[-test_count:]
    strong_algo = strong_algo_cls()
    all_prizes = 0
    total_tickets = 0
    NUM_TABLES_PER_DRAW = 8
    prizes_list = []

    for i, test_draw in enumerate(test_draws):
        available_draws = train_draws + test_draws[:i]
        combos = []
        for _ in range(NUM_TABLES_PER_DRAW):
            try:
                numbers = predict_next_numbers(available_draws, seq_len=seq_len, threshold=0.2, model_path=model_path)
                strong = strong_algo.predict(available_draws, numbers=numbers)
                combos.append({"numbers": numbers, "strong": strong})
            except Exception as e:
                logger.error(f"Arrr! [FSM GRID] Prediction failed for test draw {i}: {e}", context=f"seq_len={seq_len}, model_path={model_path}")
                continue
        for combo in combos:
            hits = sum([n in test_draw.numbers for n in combo["numbers"]])
            strong_hit = (combo["strong"] == test_draw.strong_number)
            prize = calculate_prize(hits, strong_hit)
            all_prizes += prize
            total_tickets += 1
            prizes_list.append(prize)
    total_cost = total_tickets * TICKET_COST_PER_TABLE
    roi = calculate_roi_with_tax(prizes_list, total_cost)
    return {
        "roi": roi,
        "total_prize": all_prizes,
        "total_cost": total_cost,
        "test_count": test_count
    }

def main():
    draws = load_draws()
    results = []
    param_names = list(hyperparams_grid.keys())
    best_result = None
    best_roi = float('-inf')
    for values in itertools.product(*hyperparams_grid.values()):
        params = dict(zip(param_names, values))
        model_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"sequence_classifier_grid_h{params['hidden_size']}_l{params['num_layers']}_s{params['seq_len']}_lr{params['lr']}_b{params['batch_size']}.pt")
        logger.info(f"Arrr! [FSM GRID] Trainin' with params: {params}", context=params)

        # Patch predict_next_numbers to use current params
        def predict_next_numbers_patched(draws, seq_len=10, threshold=0.5, model_path=None):
            model = LottoLSTM(
                num_numbers=37,
                seq_len=seq_len,
                hidden_size=params['hidden_size'],
                num_layers=params['num_layers']
            )
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")
            model.load_state_dict(torch.load(model_path))
            model.eval()
            seq = draws[-seq_len:]
            x_seq = []
            for d in seq:
                onehot = [0]*37
                for n in d.numbers:
                    onehot[n-1] = 1
                x_seq.append(onehot)
            x_tensor = torch.tensor([x_seq], dtype=torch.float32)
            with torch.no_grad():
                output = model(x_tensor)[0]
            pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
            numbers = [i+1 for i in pred]
            if len(numbers) > 6:
                top6 = output.topk(6).indices.tolist()
                numbers = [i+1 for i in top6]
            elif len(numbers) < 6:
                all_numbers = [n for d in draws for n in d.numbers]
                from collections import Counter
                freq = Counter(all_numbers)
                for n, _ in freq.most_common():
                    if n not in numbers:
                        numbers.append(n)
                    if len(numbers) == 6:
                        break
            return sorted(numbers)
        globals()['predict_next_numbers'] = predict_next_numbers_patched

        model = LottoLSTM(num_numbers=37, seq_len=params['seq_len'], hidden_size=params['hidden_size'], num_layers=params['num_layers'])
        need_train = True
        if os.path.exists(model_path):
            try:
                state_dict = torch.load(model_path)
                model.load_state_dict(state_dict)
                # Try a forward pass with dummy data to ensure compatibility
                dummy_input = torch.zeros((1, params['seq_len'], 37))
                model.eval()
                with torch.no_grad():
                    _ = model(dummy_input)
                logger.info(f"Arrr! [FSM GRID] Loaded existing model for {params}", context=params)
                need_train = False
            except Exception as e:
                logger.warning(f"Arrr! [FSM GRID] Model file mismatch or unusable, will retrain: {e}", context=f"seq_len={params['seq_len']}, model_path={model_path}")
                try:
                    os.remove(model_path)
                    logger.info(f"Arrr! [FSM GRID] Deleted mismatched model file: {model_path}", context=f"seq_len={params['seq_len']}, model_path={model_path}")
                except Exception as del_e:
                    logger.error(f"Arrr! [FSM GRID] Failed to delete model file: {model_path}, error: {del_e}", context=f"seq_len={params['seq_len']}, model_path={model_path}")
                if os.path.exists(model_path):
                    logger.error(f"Arrr! [FSM GRID] Model file still exists after delete attempt: {model_path}", context=f"seq_len={params['seq_len']}, model_path={model_path}")
                need_train = True
        if need_train:
            X, y = draws_to_sequences(draws, seq_len=params['seq_len'], num_numbers=37)
            criterion = torch.nn.BCELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=params['lr'])
            for epoch in range(params['epochs']):
                model.train()
                permutation = torch.randperm(X.size(0))
                for i in range(0, X.size(0), params['batch_size']):
                    indices = permutation[i:i+params['batch_size']]
                    batch_x, batch_y = X[indices], y[indices]
                    optimizer.zero_grad()
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
            torch.save(model.state_dict(), model_path)
        # For each strong number algorithm
        for strong_name, strong_cls in STRONG_NUMBER_REGISTRY.items():
            eval_result = evaluate_model(draws, model_path, params['seq_len'], strong_cls)
            result = {
                'params': params,
                'model_path': model_path,
                'strong_algo': strong_name,
                'roi': eval_result['roi'],
                'total_prize': eval_result['total_prize'],
                'total_cost': eval_result['total_cost'],
                'test_count': eval_result['test_count']
            }
            results.append(result)
            logger.info(f"Arrr! [FSM GRID] Model result: {result}", context=result)
            if result['roi'] > best_roi:
                best_roi = result['roi']
                best_result = result
    # Save all results
    with open('grid_search_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    if best_result:
        logger.info(f"Arrr! [FSM GRID] Best model: {best_result}", context=best_result)
    else:
        logger.error("Arrr! [FSM GRID] No successful models!")

    # Log the 3 models with the highest ROI
    top3 = sorted(results, key=lambda x: x['roi'], reverse=True)[:3]
    for idx, model in enumerate(top3, 1):
        logger.info(f"Arrr! [FSM GRID] Top {idx} ROI model: ROI={model['roi']}, params={model['params']}, strong_algo={model['strong_algo']}, total_prize={model['total_prize']}, total_cost={model['total_cost']}", context=model)

if __name__ == '__main__':
    main() 