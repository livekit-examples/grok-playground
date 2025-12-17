export enum ModelId {
  // Grok Realtime model
  GROK_1118 = "grok-1118",
}

export enum ModelCategory {
  REALTIME = "Realtime",
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
    name: "Grok Realtime",
    description: "xAI's realtime voice model with natural speech capabilities",
    category: ModelCategory.REALTIME,
    isNew: true,
  },
};

export const models: Model[] = Object.values(modelsData);

export const modelsByCategory: Record<ModelCategory, Model[]> = {
  [ModelCategory.REALTIME]: models.filter(m => m.category === ModelCategory.REALTIME),
};
