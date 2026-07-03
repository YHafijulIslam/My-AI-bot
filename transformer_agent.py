            import os
            
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            if os.path.exists(self.model_path):
                self.model = torch.load(self.model_path, map_location=self.device)
                self.model.eval()
                logger.info(f"✅ Transformer model loaded: {self.model_path}")
            else:
                # Create new model
                self.model = TemporalFusionTransformer(
                    input_size=5,  # OHLCV
                    d_model=64,
                    nhead=4,
                    num_layers=2,
                    forecast_horizon=self.forecast_horizon
                ).to(self.device)
                logger.info("Created new transformer model stub")
        
        except Exception as e:
            logger.error(f"Error loading transformer model: {e}")
            self.model = None
    
    def vote(self, candles: List, symbol: str = None, timeframe: str = None) -> AgentVote:
        """
        Cast vote based on transformer forecast
        """
        try:
            if not self.validate_inputs(candles):
                return self.handle_error(f"Insufficient candles: {len(candles)}")
            
            if self.model is None:
                return AgentVote(
                    agent_name=self.agent_name,
                    vote=0,
                    confidence=0.0,
                    reasoning="Transformer model not available",
                    timestamp=datetime.now(),
                    metrics={'model_available': False}
                )
            
            vote, confidence, reasoning = self._predict(candles)
            
            vote_obj = AgentVote(
                agent_name=self.agent_name,
                vote=vote,
                confidence=confidence,
                reasoning=reasoning,
                timestamp=datetime.now(),
                metrics={
                    'forecast_direction': vote,
                    'forecast_confidence': confidence,
                }
            )
            
            self.record_vote(vote_obj)
            
            return vote_obj
        
        except Exception as e:
            logger.error(f"Error in transformer vote: {e}")
            return self.handle_error(str(e))
    
    def _predict(self, candles: List) -> Tuple[int, float, str]:
        """Make transformer prediction"""
        try:
            # Prepare data
            closes = np.array([self._get_close(c) for c in candles[-self.lookback_period:]])
            highs = np.array([self._get_value(c, 'high') for c in candles[-self.lookback_period:]])
            lows = np.array([self._get_value(c, 'low') for c in candles[-self.lookback_period:]])
            opens = np.array([self._get_value(c, 'open') for c in candles[-self.lookback_period:]])
            volumes = np.array([self._get_value(c, 'volume') for c in candles[-self.lookback_period:]])
            
            # Normalize
            data = np.stack([opens, highs, lows, closes, volumes], axis=-1)
            data = (data - data.mean(axis=0, keepdims=True)) / (data.std(axis=0, keepdims=True) + 1e-7)
            
            # Convert to tensor
            x = torch.FloatTensor(data).unsqueeze(0).to(self.device)  # (1, seq_len, 5)
            
            # Forward pass to get forecast
            with torch.no_grad():
                forecast = self.model(x).cpu().numpy()[0]  # (forecast_horizon,)
            
            # Analyze forecast direction
            current_close = closes[-1]
            predicted_future_close = current_close + forecast[-1]
            
            price_change_pct = safe_divide(predicted_future_close - current_close, current_close) * 100
            threshold = 0.1  # 0.1% change threshold
            
            if price_change_pct > threshold:
                vote = 1
                confidence = min(50.0 + abs(price_change_pct) * 10, 95.0)
                reasoning = f"Transformer predicts UPWARD trend (+{price_change_pct:.2f}%) over next {self.forecast_horizon} steps"
            elif price_change_pct < -threshold:
                vote = -1
                confidence = min(50.0 + abs(price_change_pct) * 10, 95.0)
                reasoning = f"Transformer predicts DOWNWARD trend ({price_change_pct:.2f}%) over next {self.forecast_horizon} steps"
            else:
                vote = 0
                confidence = 50.0
                reasoning = f"Transformer predicts SIDEWAYS movement ({price_change_pct:.2f}%)"
                
            return vote, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Transformer prediction error: {e}")
            return 0, 0.0, f"Prediction error: {str(e)}"

    def _get_close(self, candle) -> float:
        if hasattr(candle, 'close'):
            return float(getattr(candle, 'close'))
        return float(candle.get('close', 0.0))

    def _get_value(self, candle, key: str) -> float:
        if hasattr(candle, key):
            return float(getattr(candle, key))
        return float(candle.get(key, 0.0))
