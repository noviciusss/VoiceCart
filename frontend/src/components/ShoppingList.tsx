"use client";

const CATEGORY_META: Record<string, { emoji: string; label: string }> = {
  dairy:      { emoji: "🥛", label: "Dairy" },
  produce:    { emoji: "🥬", label: "Produce" },
  beverages:  { emoji: "🧃", label: "Beverages" },
  bakery:     { emoji: "🍞", label: "Bakery" },
  meat:       { emoji: "🥩", label: "Meat & Seafood" },
  grains:     { emoji: "🌾", label: "Grains & Pasta" },
  pantry:     { emoji: "🫙", label: "Pantry" },
  snacks:     { emoji: "🍿", label: "Snacks" },
  other:      { emoji: "🛒", label: "Other" },
};

interface Item { id: string; name: string; quantity: number; unit: string; }

interface Props {
  list: Record<string, Item[]>;
  onRemove: (id: string, name: string) => void;
}

export default function ShoppingList({ list, onRemove }: Props) {
  const entries = Object.entries(list);

  if (entries.length === 0) {
    return (
      <div className="list-section">
        <p className="list-heading">Your List</p>
        <div className="empty-list">
          <div className="empty-icon">🛒</div>
          <p>Your list is empty</p>
          <p style={{ fontSize: "0.8rem", marginTop: 6, color: "var(--text-muted)" }}>
            Say something like &quot;Add 2 bottles of water&quot;
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="list-section">
      <p className="list-heading">Your List · {entries.reduce((n, [, items]) => n + items.length, 0)} items</p>
      {entries.map(([category, items]) => {
        const meta = CATEGORY_META[category] || CATEGORY_META.other;
        return (
          <div key={category} className="category-group fade-in">
            <div className="category-header">
              <span className="category-emoji">{meta.emoji}</span>
              {meta.label}
            </div>
            {items.map((item) => (
              <div key={item.id} className="item-row">
                <span className="item-name">{item.name}</span>
                <span className="quantity-badge">
                  {item.quantity}{item.unit ? ` ${item.unit}` : ""}
                </span>
                <button
                  className="remove-btn"
                  onClick={() => onRemove(item.id, item.name)}
                  aria-label={`Remove ${item.name}`}
                  id={`remove-${item.id}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
