using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace CapriPet.Views.Controls;

/// <summary>
/// Киберпанк-контейнер с фирменными асимметричными скошенными углами (45°) и угловыми засечками.
/// </summary>
public class CyberChamferBorder : Decorator
{
    public static readonly DependencyProperty BackgroundProperty =
        DependencyProperty.Register(
            nameof(Background),
            typeof(Brush),
            typeof(CyberChamferBorder),
            new FrameworkPropertyMetadata(
                new SolidColorBrush(Color.FromArgb(0xF5, 0x04, 0x00, 0x17)),
                FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty BorderBrushProperty =
        DependencyProperty.Register(
            nameof(BorderBrush),
            typeof(Brush),
            typeof(CyberChamferBorder),
            new FrameworkPropertyMetadata(
                new SolidColorBrush(Color.FromRgb(0xFE, 0x09, 0x29)),
                FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty BorderThicknessProperty =
        DependencyProperty.Register(
            nameof(BorderThickness),
            typeof(double),
            typeof(CyberChamferBorder),
            new FrameworkPropertyMetadata(
                1.5,
                FrameworkPropertyMetadataOptions.AffectsRender | FrameworkPropertyMetadataOptions.AffectsMeasure));

    public static readonly DependencyProperty AccentBrushProperty =
        DependencyProperty.Register(
            nameof(AccentBrush),
            typeof(Brush),
            typeof(CyberChamferBorder),
            new FrameworkPropertyMetadata(
                new SolidColorBrush(Color.FromRgb(0x0F, 0xFF, 0x55)),
                FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty ChamferSizeProperty =
        DependencyProperty.Register(
            nameof(ChamferSize),
            typeof(double),
            typeof(CyberChamferBorder),
            new FrameworkPropertyMetadata(
                14.0,
                FrameworkPropertyMetadataOptions.AffectsRender | FrameworkPropertyMetadataOptions.AffectsMeasure));

    public static readonly DependencyProperty PaddingProperty =
        DependencyProperty.Register(
            nameof(Padding),
            typeof(Thickness),
            typeof(CyberChamferBorder),
            new FrameworkPropertyMetadata(
                new Thickness(12, 8, 12, 8),
                FrameworkPropertyMetadataOptions.AffectsMeasure | FrameworkPropertyMetadataOptions.AffectsArrange));

    public Brush Background
    {
        get => (Brush)GetValue(BackgroundProperty);
        set => SetValue(BackgroundProperty, value);
    }

    public Brush BorderBrush
    {
        get => (Brush)GetValue(BorderBrushProperty);
        set => SetValue(BorderBrushProperty, value);
    }

    public double BorderThickness
    {
        get => (double)GetValue(BorderThicknessProperty);
        set => SetValue(BorderThicknessProperty, value);
    }

    public Brush AccentBrush
    {
        get => (Brush)GetValue(AccentBrushProperty);
        set => SetValue(AccentBrushProperty, value);
    }

    public double ChamferSize
    {
        get => (double)GetValue(ChamferSizeProperty);
        set => SetValue(ChamferSizeProperty, value);
    }

    public Thickness Padding
    {
        get => (Thickness)GetValue(PaddingProperty);
        set => SetValue(PaddingProperty, value);
    }

    protected override Size MeasureOverride(Size constraint)
    {
        double padW = Padding.Left + Padding.Right;
        double padH = Padding.Top + Padding.Bottom;

        Size childConstraint = new Size(
            Math.Max(0, constraint.Width - padW),
            Math.Max(0, constraint.Height - padH));

        if (Child != null)
        {
            Child.Measure(childConstraint);
            return new Size(
                Child.DesiredSize.Width + padW,
                Child.DesiredSize.Height + padH);
        }

        return new Size(padW, padH);
    }

    protected override Size ArrangeOverride(Size arrangeSize)
    {
        if (Child != null)
        {
            Rect childRect = new Rect(
                Padding.Left,
                Padding.Top,
                Math.Max(0, arrangeSize.Width - (Padding.Left + Padding.Right)),
                Math.Max(0, arrangeSize.Height - (Padding.Top + Padding.Bottom)));
            Child.Arrange(childRect);
        }
        return arrangeSize;
    }

    protected override void OnRender(DrawingContext dc)
    {
        double w = RenderSize.Width;
        double h = RenderSize.Height;

        if (w <= 0 || h <= 0) return;

        double c = Math.Min(ChamferSize, Math.Min(w / 3.0, h / 3.0));
        double halfStroke = BorderThickness / 2.0;

        // Фирменный контур Capri: скос в правом верхнем и левом нижнем углах
        StreamGeometry geometry = new StreamGeometry();
        using (StreamGeometryContext ctx = geometry.Open())
        {
            ctx.BeginFigure(new Point(halfStroke, halfStroke), isFilled: true, isClosed: true);
            ctx.LineTo(new Point(w - c, halfStroke), isStroked: true, isSmoothJoin: false);
            ctx.LineTo(new Point(w - halfStroke, c), isStroked: true, isSmoothJoin: false);
            ctx.LineTo(new Point(w - halfStroke, h - halfStroke), isStroked: true, isSmoothJoin: false);
            ctx.LineTo(new Point(c, h - halfStroke), isStroked: true, isSmoothJoin: false);
            ctx.LineTo(new Point(halfStroke, h - c), isStroked: true, isSmoothJoin: false);
        }
        geometry.Freeze();

        Pen borderPen = new Pen(BorderBrush, BorderThickness);
        borderPen.Freeze();

        dc.DrawGeometry(Background, borderPen, geometry);

        // Кислотно-зеленые неоновые засечки (Matrix Green) на скосах
        Pen accentPen = new Pen(AccentBrush, BorderThickness + 0.5);
        accentPen.Freeze();

        // Верхний правый скос
        dc.DrawLine(accentPen, new Point(w - c, halfStroke), new Point(w - halfStroke, c));
        // Нижний левый скос
        dc.DrawLine(accentPen, new Point(c, h - halfStroke), new Point(halfStroke, h - c));

        // Технологические угловые скобки [ ]
        double tick = Math.Min(8.0, c);
        dc.DrawLine(accentPen, new Point(halfStroke, halfStroke), new Point(halfStroke + tick, halfStroke));
        dc.DrawLine(accentPen, new Point(halfStroke, halfStroke), new Point(halfStroke, halfStroke + tick));

        dc.DrawLine(accentPen, new Point(w - halfStroke - tick, h - halfStroke), new Point(w - halfStroke, h - halfStroke));
        dc.DrawLine(accentPen, new Point(w - halfStroke, h - halfStroke - tick), new Point(w - halfStroke, h - halfStroke));
    }
}
