export enum ModelId {
  // Grok Voice Agent model
  GROK_1118 = "grok-1118",
}

export enum ModelCategory {
  VOICE_AGENT = "Voice Agent",
}

export interface Model {
  id: ModelId;
  name: string;
  description: string;
  category: ModelCategory;
  isNew?: boolean;
}

export const modelsData: Record<ModelId, Model> = {
  [ModelId.GROK_1118]: {
    id: ModelId.GROK_1118,
    name: "Grok Voice Agent",
    description: "xAI's voice model with natural speech capabilities",
    category: ModelCategory.VOICE_AGENT,
    isNew: true,
  },
};

export const models: Model[] = Object.values(modelsData);

export const modelsByCategory: Record<ModelCategory, Model[]> = {
  [ModelCategory.VOICE_AGENT]: models.filter(m => m.category === ModelCategory.VOICE_AGENT),
};
